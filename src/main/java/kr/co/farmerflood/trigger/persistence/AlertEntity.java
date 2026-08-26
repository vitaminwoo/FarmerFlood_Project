package kr.co.farmerflood.trigger.persistence;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "flood_alert")
public class AlertEntity {
    @Id public String id;
    @Column(nullable=false) public String locationId;
    @Column(nullable=false) public String locationName;
    @Column(nullable=false) public String stationCode;
    @Column(nullable=false) public String stationName;
    @Column(nullable=false) public String address;
    public int nx;
    public int ny;
    public double waterLevelMeters;
    @Column(nullable=false) public String riskLevel;
    public double forecastRainfallMm;
    public double rainfallThresholdMm;
    @Column(nullable=false) public Instant triggeredAt;
    public String userId;
    public String farmlandId;
    public Boolean productionRequested;
    @Column(length=500) public String productionDecision;
}
