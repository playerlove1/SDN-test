# Include mininet module
from mininet.log import setLogLevel, info
from mininet.net import Mininet
from mininet.cli import CLI

# define Mininet topology's function
def MininetTopo():
    # Create Net
    net = Mininet()
    # Use info to show message
    info("Create host nodes.\n")
    # Add left host h1
    lefthost = net.addHost("h1")
    # Add left host h2
    righthost = net.addHost("h2")
    
    info("Create switch node.\n")
    # Add switch 
    switch = net.addSwitch("s1", failMode = 'standalone')
    
    
    info("Create Links.\n")
    # Link h1 to s1
    net.addLink(lefthost, switch)
    # link h2 to s1
    net.addLink(righthost, switch)

    
    info("Build and start network.\n")
    # Build & Start Network
    net.build()
    net.start()
    
    
    info("Run mininet CLI.\n")
    # Open Mininet Command Line Interface 
    CLI(net)

if __name__ == '__main__':
    setLogLevel('info')
    MininetTopo()