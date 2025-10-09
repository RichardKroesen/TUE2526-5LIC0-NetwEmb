package flora.LoRaApp;

import inet.applications.contract.IApp;

simple wlam_sensor_app like IApp
{
    parameters:
        @display("i=block/app");
        double temperatureInterval 			@unit(s) = default(300s);
        double humidityInterval 			@unit(s) = default(300s);
        double no2Interval         			@unit(s) = default(600s);
        double counterInterval     			@unit(s) = default(60s);
        double intervalJitterFraction 			     = default(0.10);

        double baseTemperature        = default(20);
        double amplitudeTemperature   = default(5);
        double baseNO2                = default(15);
        double amplitudeNO2           = default(4);
        double baseHumidity           = default(50);
        double amplitudeHumidity      = default(10);

        double initialLoRaTP @unit(dBm) = default(14dBm);
        double initialLoRaCF @unit(Hz)  = default(433.375MHz);
        int    initialLoRaSF            = default(12);
        double initialLoRaBW @unit(Hz)  = default(125kHz);
        int    initialLoRaCR            = default(4);
        bool   initialUseHeader         = default(true);

        int basePayloadBytes = default(4);
		int counterPayloadBytes = default(177);

        @signal[temperature](type=double);
        @signal[no2](type=double);
        @signal[humidity](type=double);
        @signal[counter](type=long);
        @signal[LoRa_AppPacketSent](type=long);
        @statistic[temperature](source=temperature; record=vector, mean);
        @statistic[no2](source=no2; record=vector, mean);
        @statistic[humidity](source=humidity; record=vector, mean);
        @statistic[counter](source=counter; record=last, vector);
        @statistic[LoRa_AppPacketSent](source=LoRa_AppPacketSent; record=count);

    gates:
        input  socketIn  @labels(LoRaAppPacket/up);
        output socketOut @labels(LoRaAppPacket/down);
}