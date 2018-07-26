from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types

# Define class MyRyu (extend ryu.base.app_manager.RyuApp)
class MyRyu(app_manager.RyuApp):
    # Using OpenFlow protocol version 1.3
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    
    # initialize
    def __init__(self, *args, **kwargs):
        super(MyRyu, self).__init__(*args, **kwargs)
        # Record the relationship between mac and switch port 
        self.mac_to_port = {}

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        # the instance of main event message
        datapath = ev.msg.datapath
        # openflow's version
        ofproto = datapath.ofproto
        # openflow's parser 
        parser = datapath.ofproto_parser
        # parse the match
        match = parser.OFPMatch()
        # create action to controller
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        # add to flow table
        self.add_flow(datapath, 0, match, actions)
    
    # add Flow Entry
    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        if buffer_id: 
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority, match=match, instructions=inst)
        datapath.send_msg(mod)
    
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        # If you hit this you might want to increase
        # the "miss_send_length" of your switch
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes", ev.msg.msg_len, ev.msg.total_len)
        
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        # find switch in_port form message 
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return
        
        # destation mac
        dst = eth.dst
        # source mac
        src = eth.src
      
        # identify which Openflow switch connect  use datapath ID
        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

        self.logger.info("packet in %s %s %s %s", dpid, src, dst, in_port)
    
        # Learn source mac address avoid flood next time
        self.mac_to_port[dpid][src] = in_port
        
        # if dst in record
        if dst in self.mac_to_port[dpid]:
            # get the mapping switch port
            out_port = self.mac_to_port[dpid][dst]
        else:
            # flood
            out_port = ofproto.OFPP_FLOOD
        
        actions = [parser.OFPActionOutput(out_port)]

        # if not flood
        if out_port != ofproto.OFPP_FLOOD:
        
            # add to flow table avoid next time 
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
            # verify if we have a valid buffer_id, if yes avoid to send both
            # flow_mod & packet_out
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                
                self.add_flow(datapath, 1, match, actions, msg.buffer_id)
                return
            else:
                self.add_flow(datapath, 1, match, actions)
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data
        # send packet out
        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id, in_port=in_port, actions=actions, data=data)
        # send message to Openflow switch
        datapath.send_msg(out)