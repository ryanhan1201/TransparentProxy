import socket, sys, time
from threading import Thread
from urllib.parse import urlparse
from email.parser import BytesParser


sysArgs = sys.argv #index 0 is prx.py

SERVERPORT = 80

num = 1
imageFilterBool = False
PORT = int(sysArgs[1])

parser = BytesParser()

proxy = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

proxy.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

proxy.bind(('localhost', PORT))
proxy.listen(5)

def imageFilter(client_socket, client_address, response):

    return "HTTP/1.1 404 Not Found\r\nContent-Type: text/html\r\n\r\n", True

#not 1.1/1.0, Connect, HTTPS

def clientSide(request, client_socket, client_address):
    global imageFilterBool

    imageFilteredCurrently = False

    redirect = "X"

    dest_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    temp = request.split('\r\n', 1)
    requestDict = dict(parser.parsebytes(temp[1].encode()))

    requestDict["Connection"] = "close"
    requestDict["Accept-Encoding"] = ""


    splitTemp = temp[0].split(' ')

    originalClientRequest = splitTemp[0] + " " + splitTemp[1]
    parsedUrl = urlparse(splitTemp[1])

    if "image_off" in parsedUrl.query:
        imageFilterBool = True
    if "image_on" in parsedUrl.query:
        imageFilterBool = False

    imageFiltering = "X"
    if imageFilterBool:
        imageFiltering = "O"
    serverAddress = (parsedUrl.hostname, SERVERPORT)

    originalProxyRequest = originalClientRequest

    if "korea" in temp[0].lower() :
        redirect = "O"
        splitTemp[1] = "http://mnet.yonsei.ac.kr/"
        temp[0] = splitTemp[0] + " " + splitTemp[1] + " " + splitTemp[2]

        originalProxyRequest = splitTemp[0] + " " + splitTemp[1]

        modifiedRequest = temp[0] + '\r\n'

        requestDict["Host"] = "mnet.yonsei.ac.kr"

        for k,v in requestDict.items():
            modifiedRequest += (k + ": " + v + '\r\n')
        modifiedRequest += '\r\n'
        serverAddress = ("mnet.yonsei.ac.kr", SERVERPORT)
        dest_socket.connect(serverAddress)
        dest_socket.sendall(modifiedRequest.encode())
    else:
        request = temp[0] + '\r\n'

        for k,v in requestDict.items():
            request += (k + ": " + v + '\r\n')
        request += '\r\n'

        dest_socket.connect(serverAddress)
        dest_socket.sendall(request.encode())

    response = b""
    
    tempResponse = dest_socket.recv(1024)
    while tempResponse:
        response += tempResponse
        tempResponse = dest_socket.recv(1024)

    untouchedResponse = response

    decodedResponse = response.decode('utf-8', 'ignore')
    #0: is headers 1: body of split which we dont really want to deal with
    splitResponse = decodedResponse.split('\r\n\r\n')
    #0: is headers 1: body of split which we dont really want to deal with
    responseForProxy = decodedResponse.split('\r\n\r\n')
    responseForProxyHeaders = responseForProxy[0].split('\r\n')

    responseForClient = decodedResponse.split('\r\n\r\n')

    contentTypeIndex = 0
    for i in range(len(responseForProxyHeaders)):
        if "Content-Type" in responseForProxyHeaders[i]:
            contentTypeIndex = i
    
    if imageFilterBool and "image" in responseForProxyHeaders[contentTypeIndex]:
        responseForClient, imageFilteredCurrently = imageFilter(client_socket, client_address, responseForProxy)
        responseForClient = responseForClient.split('\r\n\r\n')


    responseForClientHeaders = responseForClient[0].split('\r\n')

    fullResponseForClient = responseForClient[0] + '\r\n\r\n' + responseForClient[1]

    if not imageFilteredCurrently:
        client_socket.sendall(untouchedResponse)
    else:
        client_socket.sendall(fullResponseForClient.encode())

    mimeTypeIndex = 0
    contentLenIndex = 0

    for i in range(len(responseForProxyHeaders)):
        if "Content-Type" in responseForProxyHeaders[i]:
            mimeTypeIndex = i
        if "Content-Length" in responseForProxyHeaders[i]:
            contentLenIndex = i

    dest_socket.close()
    client_socket.close()

    mimeType = responseForProxyHeaders[mimeTypeIndex].split(" ", 1)[1]
    size = responseForProxyHeaders[contentLenIndex].split(" ")[1]
    statusForProxy = responseForProxyHeaders[0].split(" ", 1)[1]
    statusForClient = responseForClientHeaders[0].split(" ", 1)[1]
    printLog(redirect, #1x
             imageFiltering, #2
             client_address, #3
             originalClientRequest, #4
             requestDict["User-Agent"], #5
             serverAddress, #6
             originalProxyRequest,#7
             requestDict["User-Agent"], #8
             statusForProxy, #9
             mimeType +" " + size, #10
             statusForClient, #11
             mimeType + " " + size,
             imageFilteredCurrently) #12

def printLog(redirected, #1
             imageFilter, #2
             clientAddress, #3
             requestFromClient, #4
             userAgentFromClient, #5
             serverAddress, #6
             requestLineToServer, #7
             userAgentToServer, #8
             statusCodeForProxy, #9
             mimeType_responseSizeForProxy, #10
             statusCodeForClient, #11
            mimeType_responseSizeForClient,
            imageFilteredCurrently): #12
    global num, imageFilterBool
    print("-----------------------------------------------")
    print(f"{num} [{redirected}] Redirected [{imageFilter}] Image filter")
    print(f"[CLI connected from {clientAddress[0]}, {clientAddress[1]}]")
    print("[CLI ==> PRX --- SRV]")
    print(f"  > {requestFromClient}")
    print(f"  > {userAgentFromClient}")
    print(f"[SRV connected to {serverAddress[0]}, {serverAddress[1]}]")
    print("[CLI --- PRX ==> SRV]")
    print(f"  > {requestLineToServer}")
    print(f"  > {userAgentToServer}")
    print("[CLI --- PRX <== SRV]")
    print(f"  > {statusCodeForProxy}")
    print(f"  > {mimeType_responseSizeForProxy} bytes")
    print("[CLI <== PRX --- SRV]")
    print(f"  > {statusCodeForClient}")
    if not imageFilteredCurrently:
    #if there was imagefiltering, then dont print next line (statusCodeForClient should be 404 not found)
        print(f"  > {mimeType_responseSizeForClient} bytes")
    print("[CLI disconnected]")
    print("[SRV disconnected]")
    num += 1



if __name__ == '__main__':
    print(f"Starting proxy server on port {PORT}")
    while True:
        try:
            client_socket, client_address = proxy.accept() #address[0] is ip address[1] is port
            request = client_socket.recv(4096).decode()
            
            splitRequest = request.split('\r\n')
            if "CONNECT" in splitRequest[0] or not ('1.1' in splitRequest[0] or '1.0' in splitRequest[0]) or "HTTPS" in splitRequest[0]:
                client_socket.close()
            else:
                print(f"Received connection from {client_address}")
                client_thread = Thread(target = clientSide, args = (request, client_socket, client_address,))
                client_thread.start()
        except KeyboardInterrupt:
            break
        time.sleep(0.1)