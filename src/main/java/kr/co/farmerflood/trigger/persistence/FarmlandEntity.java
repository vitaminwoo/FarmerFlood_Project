package kr.co.farmerflood.trigger.persistence;

import jakarta.persistence.*;
import java.time.Instant;

@Entity @Table(name="farmland")
public class FarmlandEntity {
    @Id public String id;
    @Column(nullable=false) public String userId;
    @Column(nullable=false) public String name;
    @Column(nullable=false) public String address;
    public String province;
    public String district;
    public String locality;
    public String sourceParcelId;
    public String pnu;
    public Double areaSquareMeters;
    public double latitude;
    public double longitude;
    @Column(columnDefinition="text") public String boundaryGeoJson;
    public String regionId;
    public boolean active;
    @Column(nullable=false) public Instant createdAt;
    @Column(nullable=false) public Instant updatedAt;
}
