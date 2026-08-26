package kr.co.farmerflood.trigger.persistence;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name="trigger_state")
public class TriggerStateEntity {
    @Id public String locationId;
    @Column(nullable=false) public String phase;
    @Column(nullable=false) public String riskLevel;
    public double waterLevelMeters;
    public Double forecastRainfallMm;
    public String alertId;
    @Column(length=4000) public String lastError;
    @Column(nullable=false) public Instant updatedAt;
}
