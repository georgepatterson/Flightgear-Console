import sys, DNS
import os

#query=sys.argv[1]

def resolveAddress(address):

    DNS.DiscoverNameServers()
    query=address

    reqobj=DNS.Request()

    answerobj = reqobj.req(name = query, qtype = DNS.Type.A)
    answer="Not found"
    if not len(answerobj.answers):
        if query=='localhost': #perhaps query was for localhost
            answer="127.0.0.1"
        else: #Assume that it's a Avahi address
            p = os.popen('avahi-resolve -n4 '+query +' 2>&1')
            
            line = p.readline().split("\t") #We only need the first line..
            #print line
            #print "DEBUG: Line:", line[0][0:17]
            if line[0][0:17] == "Failed to resolve":
                answer="Can't resolve"
            #else:
            if len(line)>1:
                answer=line[1].strip()
    else:
        for item in answerobj.answers:
            #print "%s %s" % (item['typename'], item['data'])
            
            answer= item['data']
            
    return answer

def ipFormatChk(ip_str):
    if len(ip_str.split()) == 1:
        ipList = ip_str.split('.')
        if len(ipList) == 4:
            for i, item in enumerate(ipList):
                try:
                    ipList[i] = int(item)
                except:
                    return False
                if not isinstance(ipList[i], int):
                    return False
            if max(ipList) < 256:
                return True
            else:
                return False
        else:
            return False
    else:
        return False
  
# True

def runtests():

    testaddress=[]

    testaddress.append("localhost") 
    testaddress.append("len01.local")
    testaddress.append("xen01.local")
    #testaddress.append("foo01.local")
    testaddress.append("www.google.com")
    #print testaddress

    for i in range(len(testaddress)):
        print "Test", testaddress[i], ":", resolveAddress(testaddress[i])
        #print "Test"+ testaddress[i] + ":"+ resolveAddress(testaddress[i]


    print ipFormatChk("127.0.0.1")
    print ipFormatChk("127.0.0.1.8")

if __name__ == "__main__":
    runtests()
