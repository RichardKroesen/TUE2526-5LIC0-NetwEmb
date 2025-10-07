package flora.simulations;

import flora.LoRaPhy.LoRaMedium;
import flora.LoraNode.LoRaNode;
import flora.LoraNode.LoRaGW;

import inet.common.geometry.common.SimpleGeographicCoordinateSystem;
import inet.visualizer.canvas.integrated.IntegratedCanvasVisualizer;

@license(LGPL);

network LoRaNetworkTest
{
    parameters:
        int numberOfNodes = default(10);
        int numberOfGateways = default(2);

        int networkSizeX = default(100);
        int networkSizeY = default(90);

        @display("bgb=10000,9000");

    submodules:
        loRaNodes[numberOfNodes]: LoRaNode {
            @display("p=2000,5000");
        }
        loRaGW[numberOfGateways]: LoRaGW {
            @display("p=5000,1000;is=s");
        }
        LoRaMedium: LoRaMedium {
            @display("p=575,92");
        }
        coordinateSystem: SimpleGeographicCoordinateSystem {
            @display("p=1136,93");
        }
        visualizer: IntegratedCanvasVisualizer {
            @display("p=1417,93");
        }
}
