import inet.common.packet.chunk.Chunk;
import inet.common.INETDefs;

namespace flora;

enum SensorBitmap
{
    SB_NONE        = 0;
    SB_TEMPERATURE = 1;
    SB_NO2         = 2;
    SB_HUMIDITY    = 4;
   	SB_TEMP_HUM	   = 5;
    SB_COUNTER     = 8;
}

class LoRaSensorPacket extends inet::FieldsChunk
{
    int bitmap @enum(SensorBitmap);

    string nodeId;
    simtime_t createdAt;

    double temperature;
    double no2;
    double humidity;
    int counter;

    char counterData[];
}