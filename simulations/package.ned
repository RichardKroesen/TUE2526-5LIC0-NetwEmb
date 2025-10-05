package flora.simulations;

import inet.applications.udpapp.UdpBasicApp;
import inet.node.inet.Router;
import inet.node.internetcloud.InternetCloud;
import flora.LoRaPhy.LoRaMedium;
import flora.LoraNode.LoRaNode;
import flora.LoraNode.LoRaGW;
import inet.node.inet.StandardHost;
import inet.networklayer.configurator.ipv4.Ipv4NetworkConfigurator;
import inet.node.ethernet.Eth1G;

import inet.common.geometry.common.SimpleGeographicCoordinateSystem;
import inet.visualizer.canvas.integrated.IntegratedCanvasVisualizer;

//package inet.examples.openstreetmap;
//
//import inet.common.geometry.common.SimpleGeographicCoordinateSystem;
//import inet.visualizer.canvas.integrated.IntegratedCanvasVisualizer;
//
//network OpenStreetMapExample
//{
//    submodules:
//        visualizer: IntegratedCanvasVisualizer {
//            parameters:
//                @display("p=100,100");
//        }
//        coordinateSystem: SimpleGeographicCoordinateSystem {
//            parameters:
//                @display("p=100,200");
//        }
//}


@license(LGPL);
network LoRaNetworkTest
{
    //* Network Parameters: *//
    parameters:
        int numberOfNodes = default(10);
        int numberOfGateways = default(2);

		//* Environment *//
        int networkSizeX = default(100);
        int networkSizeY = default(90);

		// Background Bounds
        @display("bgb=900,100");

    submodules:
        loRaNodes[numberOfNodes]: LoRaNode {
            @display("p=400,304");
        }
        loRaGW[numberOfGateways]: LoRaGW {
            @display("p=157,238;is=s");
        }
        LoRaMedium: LoRaMedium {
            @display("p=309,102");
        }
        networkServer: StandardHost {
            parameters:
                @display("p=49,44");
        }
        configurator: Ipv4NetworkConfigurator {
            parameters:
                assignDisjunctSubnetAddresses = false;
                @display("p=318,27");
        }
        internetCloud: InternetCloud {
            @display("p=231,44");
        }
        gwRouter[numberOfGateways]: Router {
            @display("p=231,134");
        }
        nsRouter: Router {
            @display("p=137,44");
        }

		// Maps
	    visualizer: IntegratedCanvasVisualizer {
            parameters:
                @display("p=100,100");
        }
        coordinateSystem: SimpleGeographicCoordinateSystem {
            parameters:
                @display("p=100,200");
        }

    connections:
        networkServer.ethg++ <--> Eth1G <--> nsRouter.ethg++;
        nsRouter.pppg++ <--> Eth1G <--> internetCloud.pppg++;
        for i=0..numberOfGateways-1 {
            internetCloud.pppg++ <--> Eth1G <--> gwRouter[i].pppg++;
            gwRouter[i].ethg++ <--> Eth1G <--> loRaGW[i].ethg++;
        }
}

