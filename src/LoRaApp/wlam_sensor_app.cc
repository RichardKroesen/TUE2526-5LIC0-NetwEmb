#include "wlam_sensor_app.h"

namespace flora {

Define_Module(wlam_sensor_app);

void wlam_sensor_app::initialize(int stage)
{
    if (stage == 0) {
        // Intervals
        double tInt  = par("temperatureInterval").doubleValue();
        double nInt  = par("no2Interval").doubleValue();
        double hInt  = par("humidityInterval").doubleValue();
        double cInt  = par("counterInterval").doubleValue();
        jitterFrac   = par("intervalJitterFraction").doubleValue();

        // Environment model parameters
        baseTemp = par("baseTemperature").doubleValue();
        ampTemp  = par("amplitudeTemperature").doubleValue();
        baseHum  = par("baseHumidity").doubleValue();
        ampHum   = par("amplitudeHumidity").doubleValue();
        baseNO2  = par("baseNO2").doubleValue();
        ampNO2   = par("amplitudeNO2").doubleValue();

        // Initial LoRa physical settings
        initTPdBm = par("initialLoRaTP").doubleValue();
        initCFHz  = par("initialLoRaCF").doubleValue();
        initSF    = par("initialLoRaSF").intValue();
        initBWHZ  = par("initialLoRaBW").doubleValue();
        initCR    = par("initialLoRaCR").intValue();

        basePayloadBytes = par("basePayloadBytes").intValue();

        // Signals
        sigTemp    = registerSignal("temperature");
        sigHum     = registerSignal("humidity");
        sigNO2     = registerSignal("no2");
        sigCounter = registerSignal("counter");
        sigPktSent = registerSignal("LoRa_AppPacketSent");

        // Locate radio
        if (auto parent = getParentModule()) {
            if (auto nic = parent->getSubmodule("LoRaNic")) {
                if (auto radio = nic->getSubmodule("radio"))
                    loRaRadio = dynamic_cast<LoRaRadio*>(radio);
            }
        }

        initSensor(SID_TEMPERATURE, tInt, false);
        initSensor(SID_NO2,        nInt, false);
        initSensor(SID_HUMIDITY,   hInt, false);
        initSensor(SID_COUNTER,    cInt, true);

        scheduler = new cMessage("sensorScheduler");
    } else if (stage == INITSTAGE_APPLICATION_LAYER) {
        applyInitialLoRaParams();
        scheduleNext();
    }
}

void wlam_sensor_app::applyInitialLoRaParams()
{
    using namespace inet::units::values;
    if (!loRaRadio) return;

    loRaRadio->loRaTP = initTPdBm;
    loRaRadio->loRaCF = Hz(initCFHz);
    loRaRadio->loRaSF = initSF;
    loRaRadio->loRaBW = Hz(initBWHZ);
    loRaRadio->loRaCR = initCR;
}

void wlam_sensor_app::initSensor(SensorID id, double interval, bool isCounter)
{
    sensors[id].id        = id;
    sensors[id].interval  = interval;
    sensors[id].isCounter = isCounter;
    sensors[id].lastValue = NAN;
    sensors[id].counter   = 0;

    if (interval > 0) {
        double jitter = interval * jitterFrac;
        sensors[id].nextDue = simTime() + interval + uniform(-jitter, jitter);
    } else {
        sensors[id].nextDue = SIMTIME_MAX;
    }
}

simtime_t wlam_sensor_app::earliestNextDue() const
{
    simtime_t e = SIMTIME_MAX;
    for (int i = 0; i < SID_COUNT; ++i)
        if (sensors[i].nextDue < e)
            e = sensors[i].nextDue;
    return e;
}

void wlam_sensor_app::scheduleNext()
{
    simtime_t n = earliestNextDue();
    if (n < SIMTIME_MAX)
        scheduleAt(n, scheduler);
}

double wlam_sensor_app::genTemperature()
{
    double hrs = simTime().dbl() / 3600.0;
    return baseTemp + ampTemp * sin(2 * M_PI * (hrs / 24.0)) + normal(0, 0.2);
}

double wlam_sensor_app::genHumidity()
{
    double hrs = simTime().dbl() / 3600.0;
    return baseHum + ampHum * sin(2 * M_PI * (hrs / 24.0) + M_PI / 4) + normal(0, 0.5);
}

double wlam_sensor_app::genNO2()
{
    double hrs = simTime().dbl() / 3600.0;
    return baseNO2 + ampNO2 * (0.5 + 0.5 * sin(2 * M_PI * (hrs / 12.0))) + normal(0, 0.1);
}

void wlam_sensor_app::attachLoRaTag(Packet *pkt)
{
    if (!loRaRadio) return;
    auto tag = pkt->addTagIfAbsent<LoRaTag>();
    tag->setSpreadFactor(loRaRadio->loRaSF);
    tag->setBandwidth(loRaRadio->loRaBW);
    tag->setCenterFrequency(loRaRadio->loRaCF);
    tag->setPower(mW(math::dBmW2mW(loRaRadio->loRaTP)));
    tag->setCodeRendundance(loRaRadio->loRaCR);
}

void wlam_sensor_app::sampleAndSendIfDue()
{
    simtime_t now = simTime();

    int bitmap = SB_NONE;
    double temperature = NAN;
    double humidity    = NAN;
    double no2         = NAN;
    int counterVal     = 0;

    for (int i = 0; i < SID_COUNT; ++i) {
        auto &s = sensors[i];
        if (s.nextDue <= now) {
            switch (s.id) {
                case SID_TEMPERATURE: {
                    temperature = genTemperature();
                    humidity    = genHumidity();
                    emit(sigTemp, temperature);
                    emit(sigHum, humidity);
                    bitmap |= SB_TEMPERATURE;
                    bitmap |= SB_HUMIDITY;
                    break;
                }
                case SID_NO2: {
                    no2 = genNO2();
                    s.lastValue = no2;
                    emit(sigNO2, no2);
                    bitmap |= SB_NO2;
                    break;
                }
                case SID_HUMIDITY: {
                    humidity = genHumidity();
                    s.lastValue = humidity;
                    emit(sigHum, humidity);
                    bitmap |= SB_HUMIDITY;
                    break;
                }
                case SID_COUNTER: {
                    s.counter++;
                    counterVal = s.counter;
                    emit(sigCounter, (long)counterVal);
                    bitmap |= SB_COUNTER;
                    break;
                }
                default:
                    break;
            }

            if (s.interval > 0) {
                double jitter = s.interval.dbl() * jitterFrac;
                s.nextDue = now + s.interval + uniform(-jitter, jitter);
            }
            else {
                s.nextDue = SIMTIME_MAX;
            }
        }
    }

    if (bitmap == SB_NONE)
        return;

    auto pkt = new Packet("sensorAggUplink");
    auto payload = makeShared<LoRaSensorPacket>();

    payload->setBitmap(bitmap);
    payload->setTemperature(temperature);
    payload->setNo2(no2);
    payload->setHumidity(humidity);
    payload->setCounter(counterVal);
    payload->setNodeId(getFullPath().c_str());
    payload->setCreatedAt(now);

    // Size accounting: base + (bitmap byte) + timestamp + present fields
    size_t bytes = basePayloadBytes + 1 + sizeof(simtime_t);
    if (bitmap & SB_TEMPERATURE) bytes += sizeof(double);
    if (bitmap & SB_NO2)         bytes += sizeof(double);
    if (bitmap & SB_HUMIDITY)    bytes += sizeof(double);
    if (bitmap & SB_COUNTER)     bytes += par("counterPayloadBytes").intValue();

    payload->setChunkLength(B(bytes));

    pkt->insertAtBack(payload);
    attachLoRaTag(pkt);
    send(pkt, "socketOut");

    emit(sigPktSent, (long)bitmap);
}

void wlam_sensor_app::handleMessage(cMessage *msg)
{
    if (msg == scheduler) {
        sampleAndSendIfDue();
        scheduleNext();
    }
    else if (msg->arrivedOn("socketIn")) {
        // Ignoring downlink packets for now
        delete msg;
    }
    else {
        delete msg;
    }
}

void wlam_sensor_app::finish()
{
    if (scheduler) {
        cancelAndDelete(scheduler);
        scheduler = nullptr;
    }
}

} // namespace flora
