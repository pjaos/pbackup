#!/usr/bin/python3

import  sys
import  os
from    optparse import OptionParser
from    subprocess import check_output, STDOUT
import  time
import  smtplib
import  socket
import  pickle
import  getpass
import  shutil
import  datetime

class BackupError(Exception):
    """@brief An excption raised during the backup process."""
    pass

class UO(object):
    """@brief responsible for user viewable output."""
    def __init__(self):
        self._logFile = None
        self._outputStore = []

    def _output(self, msg):
        """@brief Output the message to stdout and the logFile if defined"""
        print(msg)
        self.appendLog(msg)

    def appendLog(self, text):
        """@brief add the text to the log file
           @param text The text to add to the log file"""

        if self._logFile:

            fd = None
            try:
                if os.path.isfile(self._logFile):
                    fd = open(self._logFile, "a")
                else:
                    fd = open(self._logFile, "w")

                timeStamp = time.strftime("%Y-%b-%d_%H_%M_%S", time.gmtime())
                fd.write("{}: {}\n".format(timeStamp, text))
            finally:
                if fd:
                    fd.close()

    def setLog(self, logFile):
        """@brief Set the log file to be used to record all output
           @param logFile The logFile to use"""
        self._logFile = logFile

    def info(self, text):
        self._output( 'INFO:  '+str(text) )

    def debug(self, text):
        self._output( 'DEBUG: '+str(text) )

    def warn(self, text):
        self._output( 'WARN:  '+str(text) )

    def error(self, text):
        self._output( 'ERROR: '+str(text) )

class DiskUsage(object):
    """@brief Responsible for determining the disk usage."""
    def __init__(self, diskPath):
        """@brief Read the disk usage and save.
           @param diskPath The path where the disk is mounted."""
        self._totalBytes, self._usedBytes, self._freeBytes = shutil.disk_usage(diskPath)

    def getTotalGB(self):
        """@brief Get the disk size in GB
           @return The disk size in GB"""
        return self._totalBytes /(2**30)

    def getUsedGB(self):
        """@brief Get used disk space in GB
           @return The used disk space in GB"""
        return self._usedBytes /(2**30)

    def getFreeGB(self):
        """@brief Get the free disk space in GB
           @return The free disk space in GB"""
        return self._freeBytes /(2**30)

class Backup(object):
    """Responsible for providing backup functionality"""

    BACKUP_STATE_START              = 1
    BACKUP_STATE_SUCCESS            = 2
    BACKUP_STATE_ERROR              = 3

    RSYNC_CMD                       = "/usr/bin/rsync"

    FULL_BACKUP_DIR_TEXT            = "FULL"
    INCREMENTAL_BACKUP_DIR_TEXT     = "INCR"
    BACKUP_SIZE_LOG_FILE            = "backup_size.log"
    BACKUP_LOG_FILE                 = "backup.log"
    INCOMPLETE_BACKUP_SUFFIX        = "incomplete"
    NOT_STARTED_BACKUP_SUFFIX       = "not_started"

    def __init__(self, uo, options):
        """@brief Constructor
           @param uo = User output object for notifying user of progress
           @param options = Command line options
           """
        self._uo        = uo
        self._options   = options

        self._checkOptions()

    def _checkOptions(self):
        """@brief Check the required options have been entered by the user"""

        showCmdLine = self._options.show_cmd_line

        if self._options.test_email:
            if not self._options.email_server:
                raise BackupError("To test the email you must define the email server.")
            return

        #Load config is required to do so
        self._loadConfig()

        if showCmdLine:
            self.showCmdLine()

        if self._options.src == None:
            raise BackupError("Please define the src path on the command line.")

        #If the src path exists but does not end /. / at the end of the path ensures we copy the dir contents
        if  os.path.isdir(self._options.src) and not self._options.src.endswith("/"):
            self._options.src="{}/".format(self._options.src)

        if self._options.dest == None:
            raise BackupError("Please define the dest path on the command line.")

        if self._options.max_full < 2:
            raise BackupError("The minimum number of full backups that you can set is 2.")

        if self._options.max_inc < 0:
            raise BackupError("The minimum number of incremental backups cannot be negative.")

        #Ensure local dest path exists
        if not os.path.isdir(self._options.dest):
            if self._options.disable_create_dest:
                raise BackupError("{} path does not exist.".format(self._options.dest) )
            else:
                self._createDestPath()

        if self._options.save_config and self._options.load_config:
            raise BackupError("The save and load config command line options cannot be used at the same time.")

        if self._options.email_server and not self._options.email_list:
            raise BackupError("If the email server is defined then you must define the email list")

        if self._options.email_list and not self._options.email_server:
            raise BackupError("If the email list is defined then you must define the email server")

    def showCmdLine(self):
        """@brief show the command line. Useful when the user loaded the cmd line options from a file and
           needs to know the original command line"""

        optionList = []

        optionList.append( "--src  {}".format(self._options.src) )

        optionList.append( "--dest {}".format(self._options.dest) )

        if self._options.src_exclude:
            optionList.append( "--src_exclude {}".format(self._options.src_exclude) )

        if self._options.log:
            optionList.append( "--log {}".format(self._options.log) )

        if self._options.max_full:
            optionList.append( "--max_full {}".format(self._options.max_full) )

        if self._options.max_inc:
            optionList.append( "--max_inc {}".format(self._options.max_inc) )

        if self._options.email_list:
            optionList.append( "--email_list {}".format(self._options.email_list) )

        if self._options.email_server:
            optionList.append( "--email_server {}".format(self._options.email_server) )

        if self._options.email_username:
            optionList.append( "--email_username {}".format(self._options.email_username) )

        if self._options.email_password:
            optionList.append( "--email_password {}".format(self._options.email_password) )

        if self._options.pre_script:
            optionList.append( "--pre_script {}".format(self._options.pre_script) )

        if self._options.post_script:
            optionList.append( "--post_script {}".format(self._options.post_script) )

        if self._options.debug:
            optionList.append( "--debug {}".format(self._options.debug) )

        self._uo.info("Previous command line")
        print(" ".join(optionList))
        sys.exit(0)

    def _createDestPath(self):
        """@brief Create dest path if it does not exist"""
        if not os.path.isdir(self._options.dest):

            os.makedirs(self._options.dest)

            if not os.path.isdir(self._options.dest):

                raise BackupError("Failed to create dest path: {}".format(self._options.dest) )

    def _notifyEmail(self, subjectMessage, body=""):
        """@brief Responsible for notifying the user of the backup progress via email
           @param subject The subject line of the notification email
           @param body The body text of the notification email"""
        backupSrc, _ = self._getSrc()

        subject = "{}: '{}' {}".format(socket.gethostname(), backupSrc , subjectMessage)
        if self._options.email_server:
            toList = self._options.email_list.split(",")
            self._sendMail( self._options.email_server, self._options.email_username, self._options.email_password, toList, subject, body)

    def _getFullBackupID(self, backupDest):
        """@brief Given a backup dir name, extract the full backup ID
           @return The full backup ID or -1 if not found"""
        fullNum = -1

        fullBackupSubStr = ".{}".format(Backup.FULL_BACKUP_DIR_TEXT)

        pos = backupDest.find(fullBackupSubStr)

        if pos > 0:
            #Extract the full backup number
            tmpStr = backupDest[pos+1:]
            elems = tmpStr.split("_")
            try:

                fullNum = int(elems[1])

            except ValueError:
                raise BackupError("Failed to extract the full backup number from {}".format(backupDest) )

        return fullNum

    def _getLastFullBackup(self):
        """@brief Get the last full backup from the destination directory.
           @return The last full backup directory name or an empty string if no backup is present."""

        backup=""
        fullBackupID = -1

        #Check for the latest backup
        entryList = os.listdir(self._options.dest)

        for entry in entryList:
            #Get the last full complete backup
            if entry.find(".{}".format(Backup.FULL_BACKUP_DIR_TEXT) ) != -1 and entry.find(Backup.INCOMPLETE_BACKUP_SUFFIX) == -1:

                thisFullBackupID = self._getFullBackupID(entry)

                if fullBackupID == -1:

                    fullBackupID = thisFullBackupID
                    backup = entry

                elif fullBackupID < thisFullBackupID:

                    fullBackupID = thisFullBackupID
                    backup = entry

        return backup

    def _getIncBackupList(self, fullBackupID):
        """@brief Get incremental backup list for the given full backup ID
           @param fullBackupID The fuill backup ID
           @return A list of incremental backups against the given full backup"""

        incrBackupList = []

        entryList = os.listdir(self._options.dest)

        for entry in entryList:

            #If this is the correct full backup and we have found an incremental backup
            if entry.find(".{}_{}".format(Backup.FULL_BACKUP_DIR_TEXT, fullBackupID)) != -1 and entry.find(Backup.INCREMENTAL_BACKUP_DIR_TEXT) != -1:
                incrBackupList.append(entry)

        return incrBackupList

    def _getIncrBackupID(self, backupDest):
        """@brief Given a backup dir name, extract the incremental backup ID
           @return The incremental backup ID or -1 if not found"""
        incrNum = -1

        #If this incremental backup completed
        if backupDest.find(Backup.INCOMPLETE_BACKUP_SUFFIX) == -1:
            incrBackupSubStr = "_{}".format(Backup.INCREMENTAL_BACKUP_DIR_TEXT)

            pos = backupDest.find(incrBackupSubStr)

            if pos > 0:
                #Extract the incremental backup number
                tmpStr = backupDest[pos+1:]
                elems = tmpStr.split("_")
                try:

                    incrNum = int(elems[1])

                except ValueError:
                    raise BackupError("Failed to extract the incremental backup number from {}".format(backupDest) )

        return incrNum

    def _getLastIncrBackup(self, fullBackupID):
        """@brief get the last incremental backup with the given full backup ID
           @param fullBackupID The full backup ID
           @return The last incremental backup ID for the given full backup or an empty string if not found"""

        incrBackupList = self._getIncBackupList(fullBackupID)

        backup=""
        incrBackupID = -1

        #Check for the latest backup
        for entry in incrBackupList:

            thisIncrBackupID = self._getIncrBackupID(entry)
            if incrBackupID == -1:

                incrBackupID = thisIncrBackupID
                backup = entry

            elif thisIncrBackupID > incrBackupID:

                incrBackupID = thisIncrBackupID
                backup = entry

        return backup

    def _getFullBackupDest(self, fullBackupID):
        """@brief get the full backup destination path"""
        timeStamp = time.strftime("%Y-%b-%d_%H_%M_%S", time.gmtime())
        backupDest = os.path.join(self._options.dest, "{}.{}_{}".format(timeStamp, Backup.FULL_BACKUP_DIR_TEXT, fullBackupID) )
        return backupDest

    def _getIncrBackupDest(self, fullBackupID, incrBackupID):
        """@brief get the full backup destination path"""
        timeStamp = time.strftime("%Y-%b-%d_%H_%M_%S", time.gmtime())
        backupDest = os.path.join(self._options.dest, "{}.{}_{}_{}_{}".format(timeStamp, Backup.FULL_BACKUP_DIR_TEXT, fullBackupID, Backup.INCREMENTAL_BACKUP_DIR_TEXT, incrBackupID) )
        return backupDest

    def _sendMail(self, server, username, password, toList, subject, body):
        """@brief Send an email via an SMTP server
           @param server The server name (E.G smtp.gmail.com). This string can include the
                         server port number if required (E.G smtp.gmail.com:587)
           @param username The username to be used in order to log into the SMTP server
           @param password The password to be used in order to log into the SMTP server
           @param toList   A List of email addresses to send the email to
           @param subject  The subject text line of the email
           @param body     The body text of the email
        """

        # Prepare actual message
        message = """\From: {}\nTo: {}\nSubject: {}\n\n{}
        """.format(username, ", ".join(toList), subject, body)
        try:
            port = 587
            if server.find(":") != -1:
                elems = server.split(":")
                server = elems[0]
                port = int(elems[1])
            server = smtplib.SMTP("smtp.gmail.com", port) #or port 465 doesn't seem to work!
            server.ehlo()
            server.starttls()
            #If we have a username and password, login to the email server
            if username and password:
                server.login(username, password)
            server.sendmail(username, toList, message)
            server.close()
            self._uo.info("SUBJECT: {}".format( subject ) )
            self._uo.info("BODY:    {}".format( body ) )
            self._uo.info("Sent email to {} as backup status notification".format( str(toList) ) )
        except Exception as e:
            #We dont throw an error here or any error send email notifications could
            #break the backup process
            self._uo.error( e )

    def _getBackupDest(self):
        """@brief Get the backup dir name
           @return a The backup destination path

           If no backup is present in the dest folder return the intitial full backup path

           If a full backup is present but we have not reached the max number of incremental backups
           return the next incremental backup path.

           If we have reached the max number of incremental backups return the next full backup path."""

        backupDest = ""

        lastFullBackup      = self._getLastFullBackup()

        #If no full backup return full backup with ID = 1
        if len( lastFullBackup ) == 0:

            backupDest = self._getFullBackupDest(1)

        else:

            fullBackupID = self._getFullBackupID(lastFullBackup)

            incrBackup = self._getLastIncrBackup(fullBackupID)

            #If the user wishes a full backup every month and we are on the
            # first day of the month then perform a full backup.
            now = datetime.datetime.today()
            if self._options.monthly_full and now.day == 1:

                backupDest = self._getFullBackupDest(fullBackupID+1)

            #If no incremental backups are required then select next full backup
            elif self._options.max_inc == 0:

                backupDest = self._getFullBackupDest(fullBackupID+1)

            #If no incr backup return incr backup with ID = 1
            elif len(incrBackup) == 0:

                backupDest = self._getIncrBackupDest(fullBackupID, 1)

            else:
                incrBackupID = self._getIncrBackupID(incrBackup)

                #If all the incr backups have been done
                if incrBackupID >= self._options.max_inc:

                    #return the next full backup
                    backupDest = self._getFullBackupDest(fullBackupID+1)

                else:

                    backupDest = self._getIncrBackupDest(fullBackupID, incrBackupID+1)

        return backupDest

    def renameBackup(self, fullBackupID):
        """@brief Rename all backups to have a full backup ID one lower than their current full backup ID"""
        entryList = os.listdir(self._options.dest)
        for entry in entryList:
            fullBackupIDText = "{}_{}".format(Backup.FULL_BACKUP_DIR_TEXT, fullBackupID)
            newFullBackupIDText = "{}_{}".format(Backup.FULL_BACKUP_DIR_TEXT, fullBackupID-1)
            if entry.find(fullBackupIDText) != -1:
                currentPath = os.path.join(self._options.dest, entry)
                newPath     = os.path.join(self._options.dest, entry)
                newPath     = newPath.replace(fullBackupIDText, newFullBackupIDText)
                cmd = "mv {} {}".format(currentPath, newPath)
                cmdOutput = check_output(cmd, shell=True, stderr=STDOUT)
                self._uo.info(cmdOutput)
                self._uo.info("Renamed {} as {}".format(currentPath, newPath) )

    def _getFullBackupCount(self):
        """@brief Get the number of full backups currently stored in the dest location"""

        fullBackupCount = 0

        entryList = os.listdir(self._options.dest)
        for entry in entryList:
            #If this is a full backup path
            if entry.find(".{}_".format(Backup.FULL_BACKUP_DIR_TEXT) ) != -1 and entry.find("_{}_".format(Backup.INCREMENTAL_BACKUP_DIR_TEXT) ) == -1:
                fullBackupCount=fullBackupCount+1

        return fullBackupCount

    def _getBackupList(self):
        """@brief Return a list of all full and incremental backups that are stored, sorted into date order"""

        fullBackupList = []

        entryList = os.listdir(self._options.dest)
        for entry in entryList:

            if entry.find(".{}_".format(Backup.FULL_BACKUP_DIR_TEXT) ) != -1:
                fullBackupList.append(entry)

        fullBackupList.sort()

        return fullBackupList

    def _purgeBackups(self):
        """@brief A maximum number of full backups is defined. This ensure that we don't keep
                  more backups than are required. The oldest backups are removed to ensure this."""

        #Delete the old backup log file if it exists
        oldBackupLogFile = self._getBackupSizeLogFile()
        if os.path.isfile(oldBackupLogFile):
            os.remove(oldBackupLogFile)

        while self._getFullBackupCount()  > self._options.max_full:

            backupList = self._getBackupList()
            oldestBackupID = self._getFullBackupID(backupList[0])

            #Delete all backups that reference this full backup ID
            for backup in backupList:
                if backup.find(".{}_{}".format(Backup.FULL_BACKUP_DIR_TEXT, oldestBackupID)) != -1:
                    delPath = os.path.join(self._options.dest, backup)
                    cmd = "rm -rf {}".format(delPath)
                    cmdOutput = check_output(cmd, shell=True, stderr=STDOUT)
                    self._uo.info(cmdOutput)
                    self._uo.info("Removed {}".format(delPath) )

    def _getFullBackupPath(self, backupPath):
        """@brief Get the full backup path associated with this backup path.
           @param backupPath Could hold a full or incremental backup path.
                  Incremental backup paths contain the name of the associated
                  full backup path with the incremental backup ID added
           @return The Full backup path"""

        #If backupPath is a full backup path
        fullBackupIDPos = backupPath.find(".{}_".format(Backup.FULL_BACKUP_DIR_TEXT) )

        if fullBackupIDPos != -1 and backupPath.find("_{}_".format(Backup.INCREMENTAL_BACKUP_DIR_TEXT)) == -1:
            return backupPath

        #Extract the full backup ID
        if fullBackupIDPos > 0:
            elems = backupPath[fullBackupIDPos:].split("_")
            fullBackupIDStr = elems[1]
            try:
                fullBackupID = int(fullBackupIDStr)
            except:
                raise BackupError("{} is not a valid full backup ID extracted from {}".format(fullBackupIDStr, backupPath) )

            entryList = os.listdir(self._options.dest)
            for entry in entryList:
                if entry.endswith("{}_{}".format(Backup.FULL_BACKUP_DIR_TEXT, fullBackupID) ):
                    return os.path.join(self._options.dest, entry)

        else:
            raise BackupError("{} is not a valid backup path".format(backupPath) )

    def _getLastBackupPath(self, backupDest):
        """@brief Get the path of the last backup"""

        #Get the full backup path associated with this backup
        lastFullBackup = self._getFullBackupPath(backupDest)

        #Check if the last backup we had was a full backup
        pos = backupDest.find("_{}_".format(Backup.INCREMENTAL_BACKUP_DIR_TEXT) )

        if pos == -1:

            #If this is a full backup path
            if backupDest.find(".{}_".format(Backup.FULL_BACKUP_DIR_TEXT) ) != -1:

                #If so then return this backup
                return lastFullBackup

            else:

                raise BackupError("{} is not a full or incremental backup path ???".format(backupDest) )

        #Extract the incremental backup number
        incNumStr = backupDest[pos+6:]
        incNumStr.rstrip("\r")
        incNumStr.rstrip("\n")
        try:

            incNum = int(incNumStr)

        except ValueError:
            raise BackupError("Failed to extract the incremental backup number from {}".format(backupDest) )

        if incNum > 0:
            incNum = incNum -1

        #Search for this incremental backup
        lastBackupPath = None
        entryList = os.listdir(self._options.dest)
        for entry in entryList:
            if entry.endswith("_{}_{}".format(Backup.INCREMENTAL_BACKUP_DIR_TEXT, incNum)):
                lastBackupPath = entry
                break

        #If we found the incremental backup
        if lastBackupPath:
            #Build full backup path
            lastBackupPath = os.path.join(self._options.dest, lastBackupPath)
        else:
            #Use last full backup
            lastBackupPath = lastFullBackup

        return lastBackupPath

    def _getSrc(self):
        """@brief Get the backup src string.
           @return A tuple containing the backup source string followed by the sshPort (None if ssh not being used)"""

        backupSrc = self._options.src

        sshPort = None

        if self._options.ssh:

            #Build src string from user input
            hostName = self._options.ssh

            username=getpass.getuser()

            #Get the username if supplied by the user
            elems = hostName.split("@")

            if len(elems) == 2:
                username = elems[0]
                hostName=hostName[len(username)+1:]

            elems = hostName.split(":")
            if len(elems) == 2:
                sshPort = int(elems[1])
                hostName = elems[0]

            elif len(elems) == 1:
                hostName = elems[0]

            else:
                raise BackupError("{} is an invalid ssh server (E.G server or username@server or username@server:22)".format(hostName))

            backupSrc = "{}@{}:{}".format(username, hostName, self._options.src)

        return (backupSrc, sshPort)

    def _getBackupsToday(self):
        """@brief Get the number of backups that have been created today"""
        backupsToday = 0

        dayStamp = time.strftime("%Y-%b-%d_", time.gmtime())

        entryList = os.listdir(self._options.dest)
        for entry in entryList:
            if entry.find(dayStamp) != -1:
                backupsToday=backupsToday+1

        return backupsToday

    def _doBackup(self):
        """@brief Execute the rsync command to perform the backup"""
        backupDest              = None
        diskUsageBefore         = None
        diskUsageAfter          = None
        incompleteBackupDest    = None
        try:
            startTime = time.time()

            diskUsageBefore = DiskUsage(self._options.dest)
            backupDest = self._getBackupDest()
            incompleteBackupDest    = "{}.{}".format(backupDest, Backup.NOT_STARTED_BACKUP_SUFFIX)

            backupsToday = self._getBackupsToday()
            if( backupsToday >= self._options.max_daily_backups ):
                raise BackupError("{} backups have been created today. The maximum daily backup count (set on the command line) is {}. Therefore no more backups can be created today".format(backupsToday, self._options.max_daily_backups) )

            #If required run the script before the backup starts (usefull for setting up LVM snapshots)
            if self._options.pre_script:
                cmdOutput = check_output(self._options.pre_script, shell=True, stderr=STDOUT)
                self._uo.info(cmdOutput)

            backupSrc, sshPort = self._getSrc()

            self._uo.info("Backing up {} to {}".format(backupSrc, backupDest) )

            #Get the full backup path associated with this backup
            fullBackupPath = self._getFullBackupPath(backupDest)

            #If this is the full backup
            if backupDest == fullBackupPath:

                cmd="{} -avh --safe-links --delete".format(Backup.RSYNC_CMD)

            else:

                lastBackupPath = self._getLastBackupPath(backupDest)
                cmd="{} -avh --safe-links --delete --link-dest={}".format(Backup.RSYNC_CMD, lastBackupPath)

            #If the user has defined an exclusion pattern
            if self._options.src_exclude:
                exludePatternList  = self._options.src_exclude.split(",")
                for exludePattern in exludePatternList:
                    cmd="{} --exclude {}".format(cmd, exludePattern)

            #We set the backup destination with an incomplete suffix and then when the backup is complete
            #set it to the correct destination. This allows users to easily see if a backup did not complete
            incompleteBackupDest = "{}.{}".format(backupDest, Backup.INCOMPLETE_BACKUP_SUFFIX)

            if sshPort:

                cmd="{} -e \"ssh -p {} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null\" {} {}".format(cmd, sshPort, backupSrc, incompleteBackupDest)

            else:

                cmd="{} {} {}".format(cmd, backupSrc, incompleteBackupDest)

            self._notifyEmail("Backup Started", body="BACKUP COMMAND\n\n{}\n\n\nThe backup source is {}. The backup will be stored in the {} path".format(cmd, backupSrc, backupDest) )

            self._uo.info("RSYNC CMD: {}".format(cmd) )

            #Do the backup
            cmdOutput = check_output(cmd, shell=True, stderr=STDOUT)
            self._uo.info(cmdOutput)

            os.rename(incompleteBackupDest, backupDest)

            diskUsageAfter = DiskUsage(self._options.dest)
            self._saveDiskUsage(backupDest, diskUsageBefore, diskUsageAfter, startTime)

            backupCompletedMessage = "Backup Completed Successfully"
            if diskUsageAfter.getFreeGB() < (self._options.low/1E3):
                backupCompletedMessage =  "{}  !!! Low Disk Space !!!".format(backupCompletedMessage)

            self._uo.info(backupCompletedMessage)
            self._notifyEmail(backupCompletedMessage, body="This backup has been stored in the {} path\n\n\n{}".format(backupDest, self._getBackupLog() ) )

            #Purge old backups if required
            self._purgeBackups()

        finally:
            #If the backup failed, create the record of the backup space used
            if not diskUsageAfter:
                diskUsageAfter = DiskUsage(self._options.dest)
                self._saveDiskUsage(incompleteBackupDest, diskUsageBefore, diskUsageAfter, startTime)

            #If required run the script after the backup complete (usefull for closing down LVM snapshots)
            if self._options.post_script:
                cmdOutput = check_output(self._options.post_script, shell=True, stderr=STDOUT)
                self._uo.info(cmdOutput)

    def _getBackupSizeLogFile(self):
        """@return The name of the backup size log file.
                   This was the old log file name and is no longer used. If this
                   file is found then it is deleted."""
        return os.path.join(self._options.dest, Backup.BACKUP_SIZE_LOG_FILE)

    def _getBackupLogFile(self):
        """@return The name of the backup log file."""
        return os.path.join(self._options.dest, Backup.BACKUP_LOG_FILE)

    def _saveDiskUsage(self, backupDest, diskUsageBefore, diskUsageAfter, startTime):
        """@brief Save the disk usage in the dest backup dir
           @param backupDest The backup destination
           @param diskUsageBefore The disk usage before the backup was started
           @param diskUsageAfter The disk usage after the backup was completed or failed
           @param startTime The start time of the backup in seconds
           @return None"""

        thisBackupName = backupDest.split('/').pop()

        #We calc the backup size as the drop in free space wheil the backup was running.
        #Other processes could be using disk space while the backup is running but
        #for the moment this is the assumption made.
        backupSizeGB = diskUsageBefore.getFreeGB()-diskUsageAfter.getFreeGB()
        timeStr = time.strftime("%H:%M:%S", time.gmtime(time.time()-startTime) )
        backupDetails = "Disk: Free {:.1f} GB, Used {:.1f} GB, Backup Size {:.1f} GB, Took {}".format( diskUsageAfter.getFreeGB(), diskUsageAfter.getUsedGB(), backupSizeGB, timeStr)
        line = "{}: {}".format(thisBackupName, backupDetails)

        backupSizeRecordLogFile = self._getBackupLogFile()
        if os.path.isfile(backupSizeRecordLogFile):
            fd = open(backupSizeRecordLogFile, 'a')
        else:
            fd = open(backupSizeRecordLogFile, 'w')
        fd.write("{}\n".format(line) )
        fd.close()
        self._uo.info(line)

    def _getBackupLog(self):
        """@brief Get the size of the backup over time
           @return the above"""
        lines = []
        backupSizeRecordLogFile = self._getBackupLogFile()
        if os.path.isfile(backupSizeRecordLogFile):
            fd = open(backupSizeRecordLogFile, 'r')
            lines = fd.readlines()
            fd.close()

        return "".join(lines)

    def _saveConfig(self):
        """@brief Save all the command line options to a config file"""
        if self._options.save_config:
            pickle.dump( self._options, open(self._options.save_config, "wb") )
            self._uo.info("Saved command line options to {}".format(self._options.save_config) )

    def _loadConfig(self):
        """@brief Load the command line options saved previously to a config file"""
        if self._options.load_config:
            self._options = pickle.load( open(self._options.load_config, "rb") )
            self._uo.info("Loaded command line options from {}".format(self._options.load_config) )

    def execute(self):
        """@brief Called to execute the backup process"""

        if not os.path.isfile(Backup.RSYNC_CMD):
            raise BackupError("{} file not found.".format(Backup.RSYNC_CMD))

        try:

           self._doBackup()

           self._saveConfig()

        except Exception as e:
            if self._options.email_server:
                try:
                    eTextList=[]
                    #If we have some output from a check_output cmd
                    if hasattr(e, 'output'):
                        #Include this in the error text
                        eTextList.append(e.output)
                    eTextList.append( str(e) )
                    self._notifyEmail("Backup Failed", body = "{}\n\n\n{}".format("\n".join(eTextList), self._getBackupLog()) )
                except:
                    pass

            raise

    def testEmail(self):
        """@brief Send a test email"""
        self._notifyEmail("Backup Email Test", body = "TESTING BACKUP EMAIL SEND\n\n\n" )

def main():
    uo = UO()

    opts=OptionParser(usage="\n\
     A command line backup tool that provides full and incremental backups using hard links\n\
     so that folders with a complete backup history are available. Rsync (/usr/bin/rsync)\n\
     must be installed (installed by default on most Linux distributions).")

    opts.add_option("--src",                    help="Followed by the absolute path of the path to backup (required). This may include any regular expressions that can be used on the rsync src. See rsync documentation for more details of this.", default=None)
    opts.add_option("--dest",                   help="Followed by the absolute path of the path to hold the backups. (required)", default=None)
    opts.add_option("--src_exclude",            help="Followed by a comma separated list of exclude patterns to be passed to rsync in order to exclude files in the src path from the backup (optional). See rsync documentation for more details of this.", default=None)
    opts.add_option("--ssh",                    help="Followed by the src ssh host address (optional). If supplied this can include the username, E.G username@myserver (if no username is supplied the current username will be used). This may also include the SSH port number E.G username@myserver:22", default=None)
    opts.add_option("--log",                    help="Followed by the absolute path of the backup log file (optional).", default=None)
    opts.add_option("--max_full",               help="Followed by the maximum number of full backups to store (default=4).", type="int", default=4)
    opts.add_option("--max_inc",                help="Followed by the maximum number of incremental backups to store (default=92).", type="int", default=92)

    opts.add_option("--email_server",           help="Followed by the email (SMTP) server for notification of backup progress (optional). The SMTP server address can include the port number of the SMTP server (E.G smtp.gmail.com:587).", default=None)
    opts.add_option("--email_list",             help="Followed by a comma separated list of email addresses to be sent email notifications of backup progress (optional).", default=None)
    opts.add_option("--email_username",         help="Followed by the email username for notification of backup progress (optional).", default=None)
    opts.add_option("--email_password",         help="Followed by the email password for notification of backup progress (optional).", default=None)
    opts.add_option("--test_email",             help="Send a test email to check the email works.", action="store_true")

    opts.add_option("--pre_script",             help="Followed by the absolute path of a script to be executed before the backup (optional). This is usefull is LVM snapshots are used. The script can be used to create the snapshot .", default=None)
    opts.add_option("--post_script",            help="Followed by the absolute path of a script to be executed after the backup (optional). This is usefull is LVM snapshots are used. The script can be used to remove the snapshot once the backup is complete.", default=None)

    opts.add_option("--save_config",            help="Followed by the config file to save the current command line options into.", default=None)
    opts.add_option("--load_config",            help="Followed by the config file to load all command line options from. If this option is used then no other command line options are required as they will all be loaded from the config file. This allows for a simpler command line once you've got the backup you're after.", default=None)
    opts.add_option("--show_cmd_line",          help="Show the command line (excluding --save_config, --load_config --list_options) and exit. This is useful if the --load_config option is used and you wish to find the original command line.", action="store_true", default=False)
    opts.add_option("--max_daily_backups",      help="Followed by the maximum number of backups that can be taken in one day (default = 5). This ensures that no matter how many times backup is executed, the backups stored will be limited.", type="int", default=5)

    opts.add_option("--disable_create_dest",    help="Disable the creation of the dest path if it does not exist. By default the dest path is created if it does not exist", action="store_true", default=False)

    opts.add_option("--low",                    help="Low disk space threshold (MB). If the destination disk space drops below this then backup complete email messages will include a low disk space warning (default = 5000 MB).", type="int", default=5000)

    opts.add_option("--monthly_full",           help="Perform a full backup on the first day of every month. This overrides the max_inc argument.", action="store_true", default=False)

    opts.add_option("--debug",                  help="Enable debugging.", action="store_true", default=False)

    try:
        (options, args) = opts.parse_args()

        #If defined set the log file
        if options.log:
            uo.setLog(options.log)

        backup = Backup(uo, options)
        if options.test_email:
            backup.testEmail()
        else:
            backup.execute()

    #If the program throws a system exit exception
    except SystemExit:
      pass
    #Don't print error information if CTRL C pressed
    except KeyboardInterrupt:
      pass
    except Exception as e:
        eTextList=[]
        #If we have some output from a check_output cmd
        if hasattr(e, 'output'):
            eTextList.append( str(e.output) )
        eTextList.append( str(e) )
        uo.error("\n".join(eTextList))

        if options.debug:
            raise


if __name__== '__main__':
    main()
