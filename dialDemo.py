import socket
import urllib3
import requests
import json
import urllib
import xml.etree.ElementTree as ET
from io import BytesIO
from http.client import HTTPResponse

# Credits: https://stackoverflow.com/questions/47686827/how-to-parse-http-raw-bytes-and-get-the-http-content-in-python

# CHANGE THIS IF YOU HAVE A DEFAULT DIAL SERVICE IN YOUR NETWORK FOR YOUR DEMO.
# THIS WILL ALLOW YOU TO SKIP DIAL SERVICE DISCOVERY 
defaultDialRestSeviceUrl = 'http://10.0.4.215:8080/ws/app/'

class BytesIOSocket:
    def __init__(self, content):
        self.handle = BytesIO(content)

    def makefile(self, mode):
        return self.handle

def response_from_bytes(data):
    sock = BytesIOSocket(data)

    response = HTTPResponse(sock)
    response.begin()

    return urllib3.HTTPResponse.from_httplib(response)

def main():
    dialRestServiceUrl = discoverDialService()
    useDialRestService(dialRestServiceUrl)

def discoverDialService():    
    while True: 
        answer = input('Do you want to skip DIAL Service Discovery and use http://10.0.4.215:8080/ws/app/? (Y/N): ')
        if answer == 'Y': 
            return defaultDialRestSeviceUrl
        elif answer == 'N':
            break

    printTopBorder('DISCOVERING DIAL SERVICE')
    # M-SEARCH responses are DIAL devices in the same network
    mSearchReponse = requestMSearch()
    dialDevice = selectDialDevice(mSearchReponse)
    deviceDescriptionUrl = dialDevice.headers['Location']
    deviceDescriptionResponse = requestDeviceDescription(deviceDescriptionUrl)
    dialRestServiceUrl = deviceDescriptionResponse.headers['Application-URL']
    if not dialRestServiceUrl:
        print('No DIAL REST Service found.')
        exit()
    print('DIAL REST Service URL found:', dialRestServiceUrl)
    printBottomBorder('DISCOVERING DIAL SERVICE')
    return dialRestServiceUrl

def requestMSearch():
    # 5.1 M-SEARCH request (page 8-9)
    dialSearchTargetHeader = 'urn:dial-multiscreen-org:service:dial:1'
    multicastAddr = '239.255.255.250'
    multicastPort = 1900
    mSearchRequest = ("M-SEARCH * HTTP/1.1\r\n"
                    "HOST:{}:{}\r\n"
                    "ST:{}\r\n"
                    "MX:2\r\n"
                    "MAN:\"ssdp:discover\"\r\n"
                    "\r\n"
                    ).format(multicastAddr, multicastPort, dialSearchTargetHeader)
    printTopBorder('M-SEARCH REQUEST')
    print(mSearchRequest)
    printBottomBorder('M-SEARCH REQUEST')
    dialDevices = []    
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0) as s:
        s.settimeout(3)
        s.sendto(mSearchRequest.encode(), (multicastAddr, multicastPort) )
        try:
            while True:
                data, addr = s.recvfrom(65507)
                # M-SEARCH Reponse. DIAL Specification page 10.
                printTopBorder('M-SEARCH RESPONSE')
                print(data.decode())
                printBottomBorder('M-SEARCH RESPONSE')
                currentDevice = response_from_bytes(data)
                # The DIAL client SHALL use the M-SEARCH response USN (Unique Service Name) header value to deduplicate discovered DIAL servers
                isDuplicateDevice = False
                for dialDevice in dialDevices:
                    if (dialDevice.headers['USN'] == currentDevice.headers['USN']): isDuplicateDevice = True
                if (not isDuplicateDevice):
                    print('Added device. USN: {}'.format(currentDevice.headers['USN']))
                    dialDevices.append(currentDevice)
                else:
                    print('Duplicate device. USN: {}'.format(currentDevice.headers['USN']))
        except socket.timeout:
            s.close()
            pass
    return dialDevices

def selectDialDevice(dialDevices):
    printTopBorder('CHOOSE DIAL DEVICE')
    for index, dialDevice in enumerate(dialDevices):
        print('[{}] SERVER: [{}] LOCATION: [{}]'.format(index, dialDevice.headers['Server'], dialDevice.headers['Location'])) 
    
    while True:
        try:
            selectedIndex = int(input('Choose device [Exit: -1]: '))
            if selectedIndex >= 0 and selectedIndex < len(dialDevices): break
            elif selectedIndex == -1: exit()
        except ValueError:
            print('Please input a number')
    dialDevice = dialDevices[selectedIndex]
    selectedServer = dialDevice.headers['server']
    print('Selected [{}]: {}'.format(str(selectedIndex), selectedServer))
    printBottomBorder('CHOOSE DIAL DEVICE')    
    return dialDevice

def requestDeviceDescription(deviceDescriptionUrl):
    # On receipt of the M-SEARCH response, the DIAL client MAY issue an HTTP GET request to the URL
    # received in the LOCATION header of the M-SEARCH response.
    response = requests.get(deviceDescriptionUrl)   
    if not response:
        print('An error has occurred.')
        exit()

    print('Success!')
    printHttpHeaders(response.request, 'DEVICE DESCRIPTION', isRequest=True)
    printHttpHeaders(response, 'DEVICE DESCRIPTION' )
    print(response.content.decode())

    return response


def printHttpHeaders(httpMessage, name, isRequest=False):
    if isRequest:
        name = name + ' REQUEST' 
    else:
        name = name + ' RESPONSE' 
    
    printTopBorder(name)
    if isRequest:
        print('{} {}'.format(httpMessage.method, httpMessage.url))
    else:
        print('Status Code {}'.format(httpMessage.status_code))

    headers = httpMessage.headers
    for header, value in headers.items():
        print(header, ":", value)
    printBottomBorder(name)

def useDialRestService(dialRestServiceUrl):
    appInstances = []
    while True:
        command = pickCommand()
        if command == 0: exit()
        appInstances = executeCommand(command, appInstances, dialRestServiceUrl)

def pickCommand():
    while True:
        try:
            printTopBorder('PICK AN APPLICATION ACTION')
            print('(1) Query for application info\n' \
                  '(2) Launch an application\n' \
                  '(3) Close an application\n' \
                  '(4) Query all DIAL enabled app names in registry\n' \
                  '(0) End demo')
            action = int(input('Option: '))
            if action > 0 and action < 5:
                printBottomBorder('PICK AN APPLICATION ACTION')        
                return action
            elif action == 0: exit()
            else: 'Invalid selection'
        except ValueError:
            print('Please input a number')
        

def executeCommand(command, appInstances, dialRestServiceUrl):
    if command == 1:
        while True:
            appResourceUrl = getAppResourceUrl(dialRestServiceUrl)
            statusCode = queryApp(appResourceUrl)
            if (statusCode == 200):
                break
            else:
                print('Query unsuccessful, input App name again')
    elif command == 2:
        appResourceUrl = getAppResourceUrl(dialRestServiceUrl)
        appInstances = launchApp(appResourceUrl, appInstances)
    elif command == 3:
        if len(appInstances) == 0:
            print('No apps running!')
        else:    
            appToDeleteInstanceUrl = getAppIstanceUrl(appInstances)
            isDeleted = stopApp(appToDeleteInstanceUrl)
            if isDeleted: appInstances.remove(appToDeleteInstanceUrl)
    elif command == 4:
        queryAll(dialRestServiceUrl)
    return appInstances

def getAppResourceUrl(dialRestServiceUrl):
    printTopBorder('GET APPLICATION RESOURCE URL')        
    # This application name MUST be registered in the DIAL Registry
    appName = input('Insert Application Name [Default: YouTube] [Exit: Q]: ')
    if appName == 'Q': exit()
    if appName == '': appName = 'YouTube'
    if not dialRestServiceUrl.endswith('/'):
        print('Appending / to {}', dialRestServiceUrl)
        dialRestServiceUrl = dialRestServiceUrl + '/'
        print('Result: {}', dialRestServiceUrl)
    appResourceUrl = dialRestServiceUrl + appName
    print('The Application Resource URL is: {}'.format(appResourceUrl))
    printBottomBorder('GET APPLICATION RESOURCE URL')            
    return appResourceUrl

def queryApp(appResourceUrl):
    printTopBorder('QUERYING FOR APPLICATION INFORMATION')                
    # a DIAL client that wishes to discover info about an application 
    # SHALL send an HTTP GET request to the appResourceUrl
    queryString = {'clientDialVer' : '2.2'}
    appInfoQueryResponse = requests.get(appResourceUrl, params=queryString)
    printHttpHeaders(appInfoQueryResponse.request, 'DEVICE DESCRIPTION', isRequest=True)
    printHttpHeaders(appInfoQueryResponse, 'DEVICE DESCRIPTION' )
    print(appInfoQueryResponse.content.decode())
    # print('Hello')
    # root = ET.fromstring(appInfoQueryResponse.content.decode())
    # print(root.tag, root.attrib)
    # for elem in list(root):  
    #     print(elem.tag, "###", elem.attrib, "###", Uelem.text)

    printBottomBorder('QUERYING FOR APPLICATION INFORMATION')
    return appInfoQueryResponse.status_code                    

def launchApp(appResourceUrl, appInstances):
    printTopBorder('LAUNCHING APPLICATION')                    
    headers = {
        'friendlyName': 'tomato'
    }
    appLaunchResponse = requests.post(appResourceUrl, headers=headers)
    statusCode = appLaunchResponse.status_code
    printHttpHeaders(appLaunchResponse.request, 'APPLICATION LAUNCH', isRequest=True)
    printHttpHeaders(appLaunchResponse, 'APPLICATION LAUNCH' )
    # DIAL Specifications page 16-17
    if (statusCode == 404):
        print('App Recognised || Message Body || Application state')
        print('No             || any          || n/a')
    elif (statusCode == 413):
        print('App Recognised || Message Body || Application state')
        print('Yes            || too long     || n/a')
    elif (statusCode == 201):
        print('App Recognised || Message Body || Application state')
        print('Yes            || empty        || Not running or hidden')
        print('Yes            || non-empty    || Not running or hidden')
        print('APPLICATION STARTED')
        appInstanceUrl = appLaunchResponse.headers['location']
        print('The Application Instance URL is: {}'.format(appInstanceUrl))
        print('This may be used to stop the running instance of the application')
        if appInstanceUrl not in appInstances: appInstances.append(appInstanceUrl)
        print('Apps started')
        printAppInstances(appInstances)
    elif (statusCode == 200):
        print('App Recognised || Message Body || Application state')
        print('Yes            || empty        || Starting*')
        print('Yes            || non-empty    || Starting*')
        print('Yes            || empty        || Running')
        print('Yes            || non-empty    || Running')
        print('* App can be started by DIAL or by any other means, eg: built in menu')
    elif (statusCode == 501):
        print('App Recognised || Message Body || Application state')
        print('Yes            || non-empty    || Running')
        print('APPLICATION DOES NOT SUPPORT ARGUMENTS OR FAILED TO PROCESS ARGUMENTS')
    elif (statusCode == 403):
        print('App launch request from unknown DIAL client v2.1 or higher (page 17)')
    elif (statusCode == 503):
        print('Application cannot start successfully or re-started for any reason (page 17)')
    else:
        print('Status code not specified in DIAL specs, check the specs just in case')
    printBottomBorder('LAUNCHING APPLICATION')                    
    return appInstances

def getAppIstanceUrl(appInstances):
    printTopBorder('GET APPLICATION INSTANCE')                    
    printAppInstances(appInstances)
    while True:
        try:
            selectedIndex = int(input('Choose app to close [Exit: -1]: '))
            if selectedIndex >= 0 and selectedIndex < len(appInstances): break
            elif selectedIndex == -1: exit()
        except ValueError:
            print('Please input a number')
    appToDelete = appInstances[selectedIndex]
    print('Selected [{}]: {}'.format(str(selectedIndex), appToDelete))
    printBottomBorder('GET APPLICATION INSTANCE')                    
    return appToDelete

def stopApp(appToDeleteInstanceUrl):
    printTopBorder('STOPPING APPLICATION')                    
    appStopResponse = requests.delete(appToDeleteInstanceUrl)
    printHttpHeaders(appStopResponse.request, 'APPLICATION STOP', isRequest=True)
    printHttpHeaders(appStopResponse, 'APPLICATION STOP' )
    if (appStopResponse.status_code == 200 ):
        hasDeletedSuccessfully = True
    else:
        # If the response code is 404 read DIAL Specification Page 22
        print('Status code {}'.format(appStopResponse.status_code))
        hasDeletedSuccessfully = False
    printBottomBorder('STOPPING APPLICATION')    
    return hasDeletedSuccessfully

def queryAll(dialRestServiceUrl):
    printTopBorder('QUERYING ALL REGISTERED APPS NAMES')        
    lineList = [line.rstrip('\n') for line in open('appNames.txt')]
    print('There are {} apps in the registry. Not all of them may be working'.format(len(lineList)))
    for appName in lineList:
        if not dialRestServiceUrl.endswith('/'):
            print('Appending / to {}'.format(dialRestServiceUrl))
            dialRestServiceUrl = dialRestServiceUrl + '/'
            print('Result: {}'.format(dialRestServiceUrl))
        appResourceUrl = dialRestServiceUrl + appName
        appInfoQueryResponse = requests.get(appResourceUrl)
        if (appInfoQueryResponse.status_code == 200):
            print(appName)
            print(appInfoQueryResponse.content.decode())
    printBottomBorder('QUERYING REGISTERED APPS NAMES')     

def printAppInstances(appInstances):
    for index, appInstanceUrl in enumerate(appInstances):
        print('[{}] appInstanceUrl: [{}]'.format(index, appInstanceUrl)) 

def printTopBorder(text):
    print("\n=============" + text + "=============" )

def printBottomBorder(text):
    border = '=' * len("=============" + text + "=============")
    print(border + '\n')

if __name__ == '__main__':
    main()

