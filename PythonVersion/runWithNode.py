#!/usr/bin/python
###################
#mode 0:  js to js
#mode 1:  js to android
#mode 2:  android to android
#mode 3:  android to ios
#mode 4:  js to ios
#####################
'''
Created on Jan,16 2016

@author: Yanbin
'''

import sys, getopt, time
from socketIO_client import SocketIO, LoggingNamespace
import subprocess
from com.deploy import Deploy
from com.deploy_node import DeployNode
from com.serverresult import JSResultParse
from com.cleanEnv import CleanEnv
from com.getAndroidDevicesInfo import getAndroidDevice
from com.config.config import Config
from com.config.config import ConfigKeys as Keys
import psutil
import commands
import pxssh
import re
import os
from threading import Thread

print 'Number of arguments:', len(sys.argv), 'arguments.'
print 'Argument List:', str(sys.argv)

caselistfile = ''
mode = ''
install = ''
number=1
connectedNode = False
connectedNodeNumber = 0;
nodeStatus={};
nodeResult={};
try:
   opts, args = getopt.getopt(sys.argv[1:],"h:c:m:i",["help", "caselistfile=","mode=","install"])
except getopt.GetoptError:
   print 'error : run.py -c <caselistfile> -m <mode>'
   sys.exit(2)
for opt, arg in opts:
   if opt in ("-h", "--help"):
      print 'run.py -c <caselistfile> -m <mode> -i\n mode 0: JS to JS \n mode 1: JS to Android \n mode 2: Android to Android \n install:will re-install test application use the latest one, without this tag , we will not install package.'
      sys.exit()
   elif opt == "-c":
      caselistfile = arg
      print"getcaselist"
   elif opt == '-m':
      mode = arg
      print "getmode"
   elif opt == '-i':
      install = 'true'
   else:
      assert False, "unhandled option"
if caselistfile == ''or mode == '':
   print 'Error !!! \n Please use: run.py -c <caselistfile> -m <mode> \n mode 0: JS to JS \n mode 1: JS to Android \n mode 2: Android to Android'
   sys.exit()

print 'caselistfile is:', caselistfile
print 'mode is:', mode
socketServer = Config.getConfig(Keys.SOCKET_SERVER)
socketServerPort = Config.getConfig(Keys.SOCKET_SERVER_PORT)
print "socketServer is " ,socketServer
print "socketServerPort is ",socketServerPort
socketIO = SocketIO(str(socketServer), int(socketServerPort))
def start_test(filename, mode):
    target = open("TestResult.txt", 'w');
    lines = [line.rstrip('\n') for line in open(filename)]
    cleanEnv = CleanEnv();
    #cleanEnv.kill_karmaRun()
    emitmessage("lockevent",{"lock":"InitLock"})

    for index in range(len(lines)):
      interval=10
      caseinfo=split_line(lines[index]);
      print "case is", caseinfo[0];
      print "classname is", caseinfo[1];
      ######clean enviroment befor start test suits#########
      #cleanEnv.kill_karmaStart()
      #cleanEnv.kill_Firefox()
      time.sleep(5)
      socket_connect()
      if int(mode) == 0:
        print "start test js to js "  #  begining js to js test
        print "node start"
        #ssh connect to difference node and start node.py 
        deployNode=DeployNode.connect_node("yanbin-12.sh.intel.com","yanbin","yanbin","~/workspace/webrtc-webrtc-qa_new/webrtc-webrtc-qa/InteractiveTestFramework/PythonVersion","node1", mode)
        
        t = Thread(target=MyThreadWaitmessage,args=(3,))
        t.start()
        time.sleep(10)
        if t.is_alive():
          print('Still running')
        else:
          print('Completed')
          ## analysis result , if all node is finished start 
          emitmessage("lockevent",{"lock":"beginTest/"+caseinfo[0]})
          # should adjust beginTest is resolved 
          #emitmessage("lockevent",{"lock":"STARTTEST"})
          # start local testing or new node #
          deployjs2=Deploy.deploy_js("testclient2.conf.js","P2P")
          if (deployjs2 == 0):
            startjs2=Deploy.start_js("testclient2.conf.js",caseinfo[0],"P2P")
            t2 = Thread(target=WaitingPeerResult,args=(10,))
            print "startjs2 PID is: ", startjs2
            waitProcess(10,startjs2,"")
            t2.start()
            t2.join()
            case2result=JSResultParse.parseJSResult("test-results-client2.xml","P2P")
            print "case2result is ", case2result;
            JSResultParse.copyJSResult("test-results-client2.xml", caseinfo[0]+'_2',"P2P")

            if(case2result == 0):
              if (nodeResult["node1"]) == "pass":
                target.write("JS-JS case: "+caseinfo[0]+": pass");
                target.write('\n');
                print "JS-JS case: ",caseinfo[0],": pass";
              else:
                 target.write("JS-JS case: "+caseinfo[0]+": fail");
                 target.write('\n');
                 print "JS-JS case: ",caseinfo[0],": fail"
            else:
              target.write("JS-JS case: "+caseinfo[0]+": fail");
              target.write('\n');
              print "JS-JS case: ",caseinfo[0],": fail"
            cleanEnv.kill_karmaStart() # only need make sure karma start command is killed.
            emitmessage("lockevent",{"lock":"InitLock"})
          else:
            print("startBrowser error: "); 
        cleanEnv.kill_karmaStart() # only need make sure karma start command is killed.
        emitmessage("lockevent",{"lock":"InitLock"})
    ########################################################################################
    # JS to Android #
    ########################################################################################
      elif int(mode) == 1:
        print "start test JS to Android"
        deployjs1=Deploy.deploy_js("testclient1.conf.js","P2P")
        androidTestDevices=getAndroidDevice.getDevices();
        print androidTestDevices
        if install == 'true':
          deployAndroid=Deploy.deploy_android(androidTestDevices[0],"P2P")
        else:
          deployAndroid=0
        if (deployjs1 == 0) and (deployAndroid == 0):
          emitmessage("lockevent",{"lock":"STARTTEST"})
          startjs=Deploy.start_js("testclient1.conf.js",caseinfo[0],"P2P")
          print "startjs PID is: ", startjs;
          startAndorid=Deploy.start_android_sync(androidTestDevices[0],caseinfo[0],caseinfo[2],"P2P")
          waitProcess(10, startjs,startAndorid)
          case1result=JSResultParse.parseJSResult("test-results-client1.xml","P2P")
          JSResultParse.copyJSResult("test-results-client1.xml", caseinfo[0],"P2P")
          AndroidResult = getAndroidDevice.read_caselist(caseinfo[2],caseinfo[0],"P2P");
          if (case1result == 0) and (AndroidResult == 0):
            target.write("JS-Android case:: "+caseinfo[0]+": pass");
            target.write('\n');
            print "JS-Andorid case: ",caseinfo[0],": pass"
          else:
            print "JS-Android case: ",caseinfo[0],": fail"
            target.write("JS-Android case: "+caseinfo[0]+" : fail");
            target.write('\n');
        cleanEnv.kill_karmaStart() # only need make sure karma start command is killed.
        emitmessage("lockevent",{"lock":"InitLock"})
    ########################################################################################
    # Android to Android #
    ########################################################################################
      elif int(mode) == 2:
        print "start Android to Android"
        androidTestDevices=getAndroidDevice.getDevices();
        print androidTestDevices
        if install == 'true':
          deployAndroid1=Deploy.deploy_android(androidTestDevices[0],"P2P")
          deployAndroid2=Deploy.deploy_android(androidTestDevices[1],"P2P")
        else:
          deployAndroid1 = 0;
          deployAndroid2 = 0;
        if (deployAndroid1 == 0) and (deployAndroid2 == 0):
          emitmessage("lockevent",{"lock":"STARTTEST"})
          startAndroid1=Deploy.start_android_sync(androidTestDevices[0],caseinfo[0],caseinfo[1],"P2P");
          startAndroid2=Deploy.start_android_sync(androidTestDevices[1],caseinfo[0],caseinfo[2],"P2P");
          waitProcess(10, startAndroid1,startAndroid2)
          Android1Result = getAndroidDevice.read_caselist(caseinfo[1],caseinfo[0],"P2P");
          Android2Result = getAndroidDevice.read_caselist(caseinfo[2],caseinfo[0],"P2P");
          if (Android1Result == 0) and (Android2Result == 0):
            target.write("Android-Android case:: "+caseinfo[0]+": pass");
            target.write('\n');
            print "Android-Andorid case: ",caseinfo[0],": pass"
          else:
            print "Android-Android case: ",caseinfo[0],": fail"
            target.write("Android-Android case: "+caseinfo[0]+" : fail");
            target.write('\n');
        emitmessage("lockevent",{"lock":"InitLock"})

    ########################################################################################
    # Android to iOS #
    ########################################################################################
      elif int(mode) == 3:
        print "start Android to iOS"
        androidTestDevices=getAndroidDevice.getDevices();
        print androidTestDevices
        if install == 'true':
          deployiOS=Deploy.deploy_iOS('WoogeenChatTest.xcodeproj','WoogeenChatTest')
          deployAndroid1=Deploy.deploy_android(androidTestDevices[0],"P2P")
          deployiOS.prompt()
          print deployiOS.before
          deployiOS.sendline('echo $?')
          deployiOS.prompt()
          deployiOS_result=deployiOS.before.strip()
          print "$? ......"
          print deployiOS_result
          print "deployiOS pid is"
          print deployiOS.pid
          #close ssh connection
          deployiOS.close
        else:
          deployAndroid1 = 0;
          deployiOS_result = 0;
        if (deployAndroid1 == 0) and (deployiOS_result == 0):
          path="iOSResult"
          if not os.path.exists(path):
             os.mkdir(path)
          iOSResultFile = open("iOSResult/"+caseinfo[0]+'_'+caseinfo[2]+'.txt', 'w');
          print "start testing "
          emitmessage("lockevent",{"lock":"STARTTEST"})
          startAndroid1=Deploy.start_android_sync(androidTestDevices[0],caseinfo[0],caseinfo[1],"P2P");
          startiOS=Deploy.start_iOS('WoogeenChatTest.xcodeproj','WoogeenChatTest','WoogeenChatTestTests',caseinfo[0],caseinfo[2]);
          print startiOS.pid;
          # following code only use to check the android running process
          waitProcess(10,startAndroid1,"");         
          ##################################################################################
          # check iOS process
          startiOS.prompt()
          deployiOS_result=startiOS.before
          print deployiOS_result
          iOSResultFile.write(deployiOS_result);
          iOSResultFile.close()
          if(re.search("1 failed",deployiOS_result) and re.search("1 total",deployiOS_result)):
            print "match failed"
            iOSResult = 1
          elif(re.search("1 passed",deployiOS_result) and re.search("1 total",deployiOS_result)):
            print "match passed"
            iOSResult = 0
          #####################################################################################
          # compare result
          Android1Result = getAndroidDevice.read_caselist(caseinfo[1],caseinfo[0],"P2P");
          if (Android1Result == 0) and (iOSResult == 0):
            target.write("Android-iOS case:: "+caseinfo[0]+": pass");
            target.write('\n');
            print "Android-iOS case: ",caseinfo[0],": pass"
          else:
            print "Android-iOS case: ",caseinfo[0],": fail"
            target.write("Android-iOS case: "+caseinfo[0]+" : fail");
            target.write('\n');
          #########close ssh process ###########
          startiOS.close
          emitmessage("lockevent",{"lock":"InitLock"})
    ########################################################################################
    # JS to iOS #
    ########################################################################################
      elif int(mode) == 4:
        print "start JS to iOS"
        deployjs1=Deploy.deploy_js("testclient1.conf.js","P2P")
        if install == 'true':
          deployiOS=Deploy.deploy_iOS('WoogeenChatTest.xcodeproj','WoogeenChatTest')
          deployiOS.prompt()
          print deployiOS.before
          deployiOS.sendline('echo $?')
          deployiOS.prompt()
          deployiOS_result=deployiOS.before.strip()
          print "$? ......"
          print deployiOS_result
          print "deployiOS pid is"
          print deployiOS.pid
          #close ssh connection
          deployiOS.close
        else:
          deployiOS_result = 0;
        if (deployjs1 == 0) and (deployiOS_result == 0):
          iOSResultFile = open("iOSResult/"+caseinfo[0]+'_'+caseinfo[2]+'.txt', 'w');
          print "start testing "
          emitmessage("lockevent",{"lock":"STARTTEST"})
          startiOS=Deploy.start_iOS('WoogeenChatTest.xcodeproj','WoogeenChatTest','WoogeenChatTestTests',caseinfo[0],caseinfo[2]);
          print startiOS.pid;
          startjs1=Deploy.start_js("testclient1.conf.js",caseinfo[0])
          print "startjs1 PID is: ", startjs1;
          # following code only use to check the JS running process
          #############################################################################
          waitProcess(10,startjs1,"");
          ##################################################################################
          # check iOS process
          startiOS.prompt()
          deployiOS_result=startiOS.before
          #print deployiOS_result
          iOSResultFile.write(deployiOS_result);
          iOSResultFile.close()
          if(re.search("1 failed",deployiOS_result) and re.search("1 total",deployiOS_result)):
            print "match failed"
            iOSResult = 1
          elif(re.search("1 passed",deployiOS_result) and re.search("1 total",deployiOS_result)):
            print "match passed"
            iOSResult = 0
          #####################################################################################
          # compare result
          case1result=JSResultParse.parseJSResult("test-results-client1.xml","P2P")
          JSResultParse.copyJSResult("test-results-client1.xml", caseinfo[0],"P2P")
          if (case1result == 0) and (iOSResult == 0):
            target.write("JS-iOS case:: "+caseinfo[0]+": pass");
            target.write('\n');
            print "JS-iOS case: ",caseinfo[0],": pass"
          else:
            print "JS-iOS case: ",caseinfo[0],": fail"
            target.write("JS-iOS case: "+caseinfo[0]+" : fail");
            target.write('\n');
          #########close ssh process ###########
          startiOS.close
          cleanEnv.kill_karmaStart() # only need make sure karma start command is killed.
          emitmessage("lockevent",{"lock":"InitLock"})
    ########################################################################################
    # JS to Android #
    ########################################################################################
      elif int(mode) == 5:
        print "start conference test"
        #deployjs2=Deploy.deploy_js("testacular.conf2.js","CONFERENCE")
        #deployjs1=Deploy.deploy_js("testacular.conf1.js","CONFERENCE")
        
        androidTestDevices=getAndroidDevice.getDevices();
        print androidTestDevices
        if install == 'true':
          deployAndroid=Deploy.deploy_android(androidTestDevices[0],"CONFERENCE")
        else:
          deployAndroid=0
        #if (deployjs1 == 0) and (deployjs2 == 0) and (deployAndroid == 0):
        if (deployAndroid == 0):
          emitmessage("lockevent",{"lock":"STARTTEST"})
     
          #time.sleep(2)
          
          startAndorid2=Deploy.start_android_sync_remote(androidTestDevices[1],caseinfo[0],caseinfo[1],"CONFERENCE")
          startAndorid1=Deploy.start_android_sync(androidTestDevices[0],caseinfo[0],caseinfo[1],"CONFERENCE")
          startAndorid2=Deploy.start_android_sync(androidTestDevices[1],caseinfo[0],caseinfo[1],"CONFERENCE")
          startAndorid3=Deploy.start_android_sync(androidTestDevices[2],caseinfo[0],caseinfo[1],"CONFERENCE")
          #startjs2=Deploy.start_js("testacular.conf2.js",caseinfo[0],"CONFERENCE")
          time.sleep(4)
          startjs1=Deploy.start_js("testacular.conf1.js",caseinfo[0],"CONFERENCE")
          startjs2=Deploy.start_js("testacular.conf2.js",caseinfo[0],"CONFERENCE")
          print "startjs1 PID is: ", startjs1;
          #print "startjs2 PID is: ", startjs2;
          
         # waitProcess(10, startjs1,startjs2)
        #  waitProcess(10, startAndorid1,"")
          startjs1.prompt()
          print startjs1.before
          startjs1.close
          startjs2.close
          #case1result=JSResultParse.parseJSResult("test-results-client1.xml","CONFERENCE")
          #case1result=JSResultParse.parseJSResult("test-results-client2.xml","CONFERENCE")
          #JSResultParse.copyJSResult("test-results-client1.xml", caseinfo[0],"CONFERENCE")
          #JSResultParse.copyJSResult("test-results-client2.xml", caseinfo[0],"CONFERENCE")
         # AndroidResult = getAndroidDevice.read_caselist(caseinfo[1],caseinfo[0],"CONFERENCE");

          #if (case1result == 0) and (AndroidResult == 0):
          #  target.write("JS-Android case:: "+caseinfo[0]+": pass");
          #  target.write('\n');
          #  print "JS-Andorid case: ",caseinfo[0],": pass"
          #else:
          #  print "JS-Android case: ",caseinfo[0],": fail"
          #  target.write("JS-Android case: "+caseinfo[0]+" : fail");
          #  target.write('\n');
        cleanEnv.kill_karmaStart() # only need make sure karma start command is killed.
        cleanEnv.kill_Firefox()
        emitmessage("lockevent",{"lock":"InitLock"})
    ###########################################################################################
    ###########################################################################################
    # close result file #
    ###########################################################################################
    target.close()

def WaitingPeerResult(n):
  # this function is start new thread will start monitor node is connected 
    while n > 0:
      print('T-minus', n)    
      socketIO.on('lockevent', waitingPeerResultCallBack);
      print "waiting ...."      
      n-=1
      socketIO.wait(seconds=2)
def waitingPeerResultCallBack(*args):
    #print('nodeStarted',args)
    #print "value is _____________________***********"
    #print args[0]['lock']
    lockValue = args[0]['lock']
    global connectedNode 
    if re.search("pass",lockValue) != None or re.search("fail",lockValue) != None :
      print "lockValue is ", lockValue;
      nodeName, nodeAction = lockValue.split("_");
      global nodeResult
      nodeResult[nodeName] = nodeAction
      print "nodeName is ", nodeName
      print "nodeAction is ",nodeAction
      print "nodeStatus is ", nodeResult[nodeName]
    return 0 

def MyThreadWaitmessage(n):
  # this function is start new thread will start monitor node is connected 
    while n > 0:
      print('T-minus', n)    
      socketIO.on('lockevent', waitMessageCallback);
      print "waiting ...."      
      n-=1
      socketIO.wait(seconds=2)

def split_line(text):
    casenumber, casename = text.split("=")
    if casename:
       caseInfoList = casename.split(";");
       caseInfoList[0] = caseInfoList[0].replace("\"", "");
       caseInfoList[-1] = caseInfoList[-1].replace("\"", "");
       return caseInfoList

def on_aaa_response(*args):
    print('connected', args)
    return 0;
def socket_connect():
    socketIO.on('connect', on_aaa_response)
    socketIO.wait(seconds=3)
    return socketIO;
    socketIO.emit("lockevent",{"lock":"STARTTEST"})
def emitmessage(message,data):
    socketIO.emit(message,data)

def waitMessageCallback(*args):
    #print('nodeStarted',args)
    #print "value is _____________________***********"
    #print args[0]['lock']
    lockValue = args[0]['lock']
    global connectedNode 
    if re.search("connected",lockValue) != None:
      print "lockValue is ", lockValue;
      nodeName, nodeAction = lockValue.split("_");
      global nodeStatus
      nodeStatus[nodeName] = nodeAction
      print "nodeName is ", nodeName
      print "nodeAction is ",nodeAction
      print "nodeStatus is ", nodeStatus[nodeName]
    return 0 

def waitmessage(message):
    socketIO.on('lockevent', waitMessageCallback);
    socketIO.wait(seconds=5);
def waitNodeProcess(interval, processgroup):
    print_ts("-"*100)
    print_ts("Starting every %s seconds."%interval)
    print_ts("-"*100)
    global number
    total_finished = 0;
    while number < 10:
      print "****waiting time is:", number*interval, "s";
      time_remaining = interval-time.time()%interval
      print_ts("Sleeping until %s (%s seconds)..."%((time.ctime(time.time()+time_remaining)), time_remaining))
      time.sleep(time_remaining)
      print_ts("Starting command.")
      for element in processgroup:
         if element == finished :
             total_finished = total_finished + 1
      if len(my_list) == total_finished:
        total_finished = 0;
        break
      number=number+1
def print_ts(message):
    print "[%s] %s"%(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), message)
def waitProcess(interval, processnumber1,processnumber2):
    print_ts("-"*100)
    print_ts("Starting every %s seconds."%interval)
    print_ts("-"*100)
    global number
    while number < 10:
      print "****waiting time is:", number*interval, "s";
      time_remaining = interval-time.time()%interval
      print_ts("Sleeping until %s (%s seconds)..."%((time.ctime(time.time()+time_remaining)), time_remaining))
      time.sleep(time_remaining)
      print_ts("Starting command.")
      p=psutil.pids();
      print p
      if processnumber2:
        if (processnumber1 in p) or (processnumber2 in p):
          print_ts("-"*100)
          print("process ",processnumber1,',',processnumber2," still running");
          print("process ",processnumber1,"status is, ",psutil.Process(processnumber1).status());
          print("process ",processnumber2,"status is, ",psutil.Process(processnumber2).status());
          if (psutil.Process(processnumber1).status() == 'zombie') and (psutil.Process(processnumber2).status() == 'zombie'):
            break
        else:
          break
      else:
        print "*****only need detect single process", processnumber1
        if (processnumber1 in p):
          print_ts("-"*100)
          print("process ",processnumber1," still running");
          print("process ",processnumber1,"status is, ",psutil.Process(processnumber1).status());
          if (psutil.Process(processnumber1).status() == 'zombie'):
            break
        else:
          break
      number=number+1
start_test(caselistfile,mode)
#test#
#if __name__ == "__main__":
#    start_test(caselist,0)
