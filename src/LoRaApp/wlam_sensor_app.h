#ifndef __FLORA_WLAM_SENSOR_APP_H_
#define __FLORA_WLAM_SENSOR_APP_H_

#include <omnetpp.h>
#include <cstdint>
#include "inet/common/lifecycle/ILifecycle.h"
#include "inet/common/lifecycle/LifecycleOperation.h"

#include "LoRa/LoRaRadio.h"
#include "LoRa/LoRaTagInfo_m.h"
#include "DataPacket_m.h"
#include "inet/common/Units.h"

using namespace omnetpp;
using namespace inet;

namespace flora {

enum SensorID { SID_TEMPERATURE=0, SID_NO2=1, SID_HUMIDITY=2, SID_COUNTER=3, SID_COUNT=4 };

struct SensorState {
    SensorID   id;
    simtime_t  interval = 0;
    simtime_t  nextDue  = SIMTIME_MAX;
    double     lastValue = NAN;
    int        counter = 0;    // simple int
    bool       isCounter = false;
};

class wlam_sensor_app : public cSimpleModule, public ILifecycle
{
  private:
    cMessage *scheduler = nullptr;
    SensorState sensors[SID_COUNT];
    double jitterFrac = 0.0;

    // Environment generation params
    double baseTemp = 0, ampTemp = 0;
    double baseNO2 = 0, ampNO2 = 0;
    double baseHum = 0, ampHum = 0;

    // Initial LoRa params
    double initTPdBm = 0;
    double initCFHz  = 0;
    int    initSF    = 0;
    double initBWHZ  = 0;
    int    initCR    = 0;
    bool   initUseHeader = true;

    int basePayloadBytes = 0;

    // Signals
    simsignal_t sigTemp;
    simsignal_t sigNO2;
    simsignal_t sigHum;
    simsignal_t sigCounter;
    simsignal_t sigPktSent;

    LoRaRadio *loRaRadio = nullptr;

  protected:
    virtual void initialize(int stage) override;
    virtual int numInitStages() const override { return NUM_INIT_STAGES; }
    virtual void handleMessage(cMessage *msg) override;
    virtual void finish() override;
    virtual bool handleOperationStage(LifecycleOperation *operation, IDoneCallback *doneCallback) override { return true; }

    void initSensor(SensorID id, double interval, bool isCounter=false);
    simtime_t earliestNextDue() const;
    void scheduleNext();
    void sampleAndSendIfDue();

    double genTemperature();
    double genNO2();
    double genHumidity();

    void applyInitialLoRaParams();
    void attachLoRaTag(Packet *pkt);

  public:
    wlam_sensor_app() = default;
};

} // namespace flora

#endif
