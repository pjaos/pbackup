# pbackup
A command line tool that backs up data to date/time named folders so that a
history of the changes is directly available using the minimum of disk space.
A mixture of full and incremental backups can be defined. pbackup uses rsync
to perform the backup operations. Therefore rysync that must be installed
before pbackup is installed.

# Using pbackup

pbackup is a command line tool. The minimum command line options that are
required are the --src and --dest. The --src argument defines the backup
source path. All the files and folders in this folder will be copied to the
folder defined by the --dest (backup destination path) argument.

E.G

If the folder /home/auser exists containing the following

```
auser@amachine:/home/auser# ls -altR
.:
total 12
drwxr-xr-x 2 root root 4096 Jun  2 06:44 folder1
drwxr-xr-x 3 root root 4096 Jun  2 06:43 .
-rw-r--r-- 1 root root    0 Jun  2 06:43 file1.txt
drwxr-xr-x 7 root root 4096 Jun  2 06:43 ..

./folder1:
total 8
drwxr-xr-x 2 root root 4096 Jun  2 06:44 .
-rw-r--r-- 1 root root    0 Jun  2 06:44 file2.txt
drwxr-xr-x 3 root root 4096 Jun  2 06:43 ..
```

and the following command is executed

```
pbackup --src /home/auser --dest /tmp/backup_folder
INFO:  Backing up /home/auser/ to /tmp/backup_folder/2022-Jun-02_06_03_45.FULL_1
INFO:  RSYNC CMD: /usr/bin/rsync -avh --safe-links --delete /home/auser/ /tmp/backup_folder/2022-Jun-02_06_03_45.FULL_1.incomplete
INFO:  sending incremental file list
INFO:  created directory /tmp/backup_folder/2022-Jun-02_06_03_45.FULL_1.incomplete
INFO:  file1.txt
INFO:  folder1/
INFO:  folder1/file2.txt
INFO:  
INFO:  sent 242 bytes  received 145 bytes  774.00 bytes/sec
INFO:  total size is 10  speedup is 0.03
INFO:  
INFO:  Changed /tmp/backup_folder/2022-Jun-02_06_03_45.FULL_1.incomplete to /tmp/backup_folder/2022-Jun-02_06_03_45.FULL_1
INFO:  2022-Jun-02_06_03_45.FULL_1: Disk: Free 1071.0 GB, Used 668.1 GB, Backup Size 0.0 GB, Took 00:00:00
INFO:  Backup Completed Successfully
```

After running the above command the backup folder contains

```
cd /tmp/backup_folder/
auser@amachine:/tmp/backup_folder# ls -altR
.:
total 56
drwxr-xr-x  3 root root  4096 Jun  2 07:03 .
-rw-r--r--  1 root root   100 Jun  2 07:03 backup.log
drwxr-xr-x  3 root root  4096 Jun  2 07:03 2022-Jun-02_06_03_45.FULL_1
drwxrwxrwt 48 root root 40960 Jun  2 07:00 ..

./2022-Jun-02_06_03_45.FULL_1:
total 16
drwxr-xr-x 3 root root 4096 Jun  2 07:03 ..
-rw-r--r-- 1 root root    5 Jun  2 07:03 file1.txt
drwxr-xr-x 3 root root 4096 Jun  2 07:03 .
drwxr-xr-x 2 root root 4096 Jun  2 06:44 folder1

./2022-Jun-02_06_03_45.FULL_1/folder1:
total 12
-rw-r--r-- 1 root root    5 Jun  2 07:03 file2.txt
drwxr-xr-x 3 root root 4096 Jun  2 07:03 ..
drwxr-xr-x 2 root root 4096 Jun  2 06:44 .
```

As is shown above initially a full backup folder is created.

If a file is added to the backup folder and a backup is performed an incremental backup folder is created.

E.G

```
auser@amachine:/home/auser# cp /home/auser/file1.txt /home/auser/file3.txt
auser@amachine:/home/auser# pbackup --src /home/auser --dest /tmp/backup_folder
INFO:  Backing up /home/auser/ to /tmp/backup_folder/2022-Jun-02_06_06_33.FULL_1_INCR_1
INFO:  RSYNC CMD: /usr/bin/rsync -avh --safe-links --delete --link-dest=/tmp/backup_folder/2022-Jun-02_06_03_45.FULL_1 /home/auser/ /tmp/backup_folder/2022-Jun-02_06_06_33.FULL_1_INCR_1.incomplete
INFO:  sending incremental file list
INFO:  created directory /tmp/backup_folder/2022-Jun-02_06_06_33.FULL_1_INCR_1.incomplete
INFO:  file3.txt
INFO:  
INFO:  sent 208 bytes  received 126 bytes  668.00 bytes/sec
INFO:  total size is 15  speedup is 0.04
INFO:  
INFO:  Changed /tmp/backup_folder/2022-Jun-02_06_06_33.FULL_1_INCR_1.incomplete to /tmp/backup_folder/2022-Jun-02_06_06_33.FULL_1_INCR_1
INFO:  2022-Jun-02_06_06_33.FULL_1_INCR_1: Disk: Free 1071.0 GB, Used 668.1 GB, Backup Size 0.0 GB, Took 00:00:00
INFO:  Backup Completed Successfully
```

The contents of the 2022-Jun-02_05_59_02.FULL_1_INCR_1 folder is shown below. The only extra disk space used is that to store the file3.txt file.

```
auser@amachine:/tmp/backup_folder/2022-Jun-02_06_06_33.FULL_1_INCR_1# ls -altR
.:
total 20
drwxr-xr-x 4 root root 4096 Jun  2 07:06 ..
drwxr-xr-x 3 root root 4096 Jun  2 07:05 .
-rw-r--r-- 1 root root    5 Jun  2 07:05 file3.txt
-rw-r--r-- 2 root root    5 Jun  2 07:03 file1.txt
drwxr-xr-x 2 root root 4096 Jun  2 06:44 folder1

./folder1:
total 12
drwxr-xr-x 3 root root 4096 Jun  2 07:05 ..
-rw-r--r-- 2 root root    5 Jun  2 07:03 file2.txt
drwxr-xr-x 2 root root 4096 Jun  2 06:44 .
```

This shows the basic functionality of pbackup creating full and incremental backups.

By default 92 incremental backups are created before another full backup is created. This can be changed on the command line using the --max_inc command line option. The --max_full command line option sets the maximum number of full backups (default = 4) that will be stored in the destination folder. Once this limit is reached older backups are removed.

# Backing up from data from a remote machine

The remote machine must have an ssh server running and have rsync installed. To backup from a remote machine the --ssh command line argument is used. When a remote machine is defined the backup source will reside on a remote machine and the data will be pulled to the local machine.

If you wish the backup from a remote machine the --ssh command line argument must be used.

E.G

```
pbackup --src /home/auser/Documents --ssh auser@192.168.1.92:22 --dest /tmp/backup_folder/
INFO:  Backing up auser@192.168.1.92:/home/auser/Documents/ to /tmp/backup_folder/2022-Jun-02_07_19_40.FULL_1
INFO:  RSYNC CMD: /usr/bin/rsync -avh --safe-links --delete -e "ssh -p 22 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null" auser@192.168.1.92:/home/auser/Documents/ /tmp/backup_folder/2022-Jun-02_07_19_40.FULL_1.incomplete
INFO:  Warning: Permanently added '192.168.1.92' (ECDSA) to the list of known hosts.
INFO:  receiving incremental file list
INFO:  created directory /tmp/backup_folder/2022-Jun-02_07_19_40.FULL_1.incomplete
INFO:  a_document.txt
INFO:  
INFO:  sent 46 bytes  received 134 bytes  120.00 bytes/sec
INFO:  total size is 5  speedup is 0.03
INFO:  
INFO:  Changed /tmp/backup_folder/2022-Jun-02_07_19_40.FULL_1.incomplete to /tmp/backup_folder/2022-Jun-02_07_19_40.FULL_1
INFO:  2022-Jun-02_07_19_40.FULL_1: Disk: Free 1071.1 GB, Used 668.0 GB, Backup Size 0.0 GB, Took 00:00:00
INFO:  Backup Completed Successfully
```

# Sending an email

pbackup allows the user to send emails when the backup process starts and when the backup process completes. The completion email details the disk space used for that backup and the free space on the destination file system.

The following arguments can be added to the command line in order to send an email as detailed above.

```
   --email_server=<smtp server>
   --email_username=<username>
   --email_password=<password>
```

The following command line argument can be defined to set a comma separated list of email addresses to send emails to.

```
--email_list
```

The --test_email command line argument can be added to the command line in order to check that the email send process works correctly.

E.G

```
   pbackup --email_server=smtp.gmail.com:587 --email_username=auser --email_password=apassword --email_list asomeuser@adom.com --test_email
```


## Command line help
pbackup supports the -h/--help command line arguemnt to display the help text as shown below.

```
pbackup -h
Usage:
     A command line backup tool that provides full and incremental backups using hard links
     so that folders with a complete backup history are available using a minimum of storage space.
     Rsync (/usr/bin/rsync) must be installed (installed by default on most Linux distributions).

Options:
  -h, --help            show this help message and exit
  --src=SRC             Followed by the absolute path of the path to backup
                        (required). This may include any regular expressions
                        that can be used on the rsync src. See rsync
                        documentation for more details of this.
  --dest=DEST           Followed by the absolute path of the path to hold the
                        backups. (required)
  --src_exclude=SRC_EXCLUDE
                        Followed by a comma separated list of exclude patterns
                        to be passed to rsync in order to exclude files in the
                        src path from the backup (optional). See rsync
                        documentation for more details of this.
  --ssh=SSH             Followed by the src ssh host address (optional). If
                        supplied this can include the username, E.G
                        username@myserver (if no username is supplied the
                        current username will be used). This may also include
                        the SSH port number E.G username@myserver:22
  --log=LOG             Followed by the absolute path of the backup log file
                        (optional).
  --max_full=MAX_FULL   Followed by the maximum number of full backups to
                        store (default=4).
  --max_inc=MAX_INC     Followed by the maximum number of incremental backups
                        to store (default=92).
  --email_server=EMAIL_SERVER
                        Followed by the email (SMTP) server for notification
                        of backup progress (optional). The SMTP server address
                        can include the port number of the SMTP server (E.G
                        smtp.gmail.com:587).
  --email_list=EMAIL_LIST
                        Followed by a comma separated list of email addresses
                        to be sent email notifications of backup progress
                        (optional).
  --email_username=EMAIL_USERNAME
                        Followed by the email username for notification of
                        backup progress (optional).
  --email_password=EMAIL_PASSWORD
                        Followed by the email password for notification of
                        backup progress (optional).
  --test_email          Send a test email to check the email works.
  --pre_script=PRE_SCRIPT
                        Followed by the absolute path of a script to be
                        executed before the backup (optional). This is usefull
                        is LVM snapshots are used. The script can be used to
                        create the snapshot .
  --post_script=POST_SCRIPT
                        Followed by the absolute path of a script to be
                        executed after the backup (optional). This is usefull
                        is LVM snapshots are used. The script can be used to
                        remove the snapshot once the backup is complete.
  --save_config=SAVE_CONFIG
                        Followed by the config file to save the current
                        command line options into.
  --load_config=LOAD_CONFIG
                        Followed by the config file to load all command line
                        options from. If this option is used then no other
                        command line options are required as they will all be
                        loaded from the config file. This allows for a simpler
                        command line once you've got the backup you're after.
  --show_cmd_line       Show the command line (excluding --save_config,
                        --load_config --list_options) and exit. This is useful
                        if the --load_config option is used and you wish to
                        find the original command line.
  --max_daily_backups=MAX_DAILY_BACKUPS
                        Followed by the maximum number of backups that can be
                        taken in one day (default = 5). This ensures that no
                        matter how many times backup is executed, the backups
                        stored will be limited.
  --disable_create_dest
                        Disable the creation of the dest path if it does not
                        exist. By default the dest path is created if it does
                        not exist
  --low=LOW             Low disk space threshold (MB). If the destination disk
                        space drops below this then backup complete email
                        messages will include a low disk space warning
                        (default = 5000 MB).
  --monthly_full        Perform a full backup on the first day of every month.
                        This overrides the max_inc argument.
  --debug               Enable debugging.
```
