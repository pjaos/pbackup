import  datetime
import  shutil
import  os
from    time import sleep

def info(msg):
    print("INFO:  {}".format(msg))

dest = "/tmp/pbackup_test"
days = 96

now = datetime.datetime.today()
then = now - datetime.timedelta(days=days)

if os.path.isdir(dest):
    shutil.rmtree(dest)
    info("Removed {}".format(dest))

fullBUID = 1
dt = then
while dt < now:
    dt = dt + datetime.timedelta(days=1)
    timeStamp = dt.strftime("%Y-%b-%d_%H_%M_%S")
    if dt.day == 1:
        fullBUID = fullBUID + 1
        dirName = "{}.FULL_{}".format(timeStamp, fullBUID)
        sleep(1)
    else:
        dirName = "{}.FULL_{}_INCR_{}".format(timeStamp, fullBUID, dt.day-1)
    absDest = os.path.join(dest, dirName)
    os.makedirs(absDest)
    info("Created {}".format(absDest))
