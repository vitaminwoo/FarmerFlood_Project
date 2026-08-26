package kr.co.farmerflood.trigger.persistence;

import jakarta.persistence.*;
import java.time.Instant;

@Entity @Table(name="farmland_monitoring_station",uniqueConstraints=@UniqueConstraint(columnNames={"farmlandId","stationCode"}))
public class FarmlandStationEntity {
    @Id public String id;
    @Column(nullable=false) public String farmlandId;
    @Column(nullable=false) public String stationCode;
    @Column(nullable=false) public String stationName;
    public double stationLatitude;
    public double stationLongitude;
    public double distanceMeters;
    public int priorityOrder;
    public boolean active;
    @Column(nullable=false) public Instant linkedAt;
}
