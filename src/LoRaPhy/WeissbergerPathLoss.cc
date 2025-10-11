//
// SPDX-License-Identifier: LGPL-3.0-or-later
//
//
/***************************************************************************
* author:      Oliver Graute, Andreas Kuntz, Felix Schmidt-Eisenlohr
*
* copyright:   (c) 2008 Institute of Telematics, University of Karlsruhe (TH)
*
* author:      Alfonso Ariza
*              Malaga university
*
***************************************************************************/

#include "inet/physicallayer/wireless/common/pathloss/FreeSpacePathLoss.h"


namespace flora {
using namespace inet;
using namespace inet::physicallayer;

class WeissbergerPathLoss : public FreeSpacePathLoss
{
  protected:
    /**  Computes total path loss = FSPL + vegetation loss  **/
    virtual double computePathLoss(mps distance, Hz frequency) const override {
        // --- 1. Free-space path loss from parent ---
        double fspl = FreeSpacePathLoss::computePathLoss(distance, frequency);

        // --- 2. Retrieve vegetation depth parameter (in metres) ---
        // You can assign this per-simulation, per-region, or per-link.
        double vegDepth = par("vegetationDepth").doubleValue();   // metres of foliage

        // --- 3. Weissberger vegetation attenuation (in dB) ---
        // f in GHz, valid for 0 < d = 400 m
        double fGHz = frequency.get() / 1e9;
        double Lveg = 0.0;
        if (vegDepth > 0) {
            if (vegDepth <= 14.0)
                Lveg = 0.45 * std::pow(fGHz, 0.284) * vegDepth;
            else
                Lveg = 1.33 * std::pow(fGHz, 0.284) * std::pow(vegDepth, 0.588);
        }

        // --- 4. Total path loss ---
        double totalLoss = fspl + Lveg;
        return totalLoss;
    }
};

// Register this as an OMNeT++ module type
Define_Module(WeissbergerPathLoss);

} // namespace flora

