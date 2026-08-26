package kr.co.farmerflood.trigger.persistence;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name="video_production_job")
public class VideoJobEntity {
    @Id public String id;
    @Column(nullable=false,unique=true) public String alertId;
    @Column(nullable=false) public String storageName;
    @Column(nullable=false) public String status;
    public String workerJobId;
    public String currentStage;
    public String finalVideoPath;
    public String mediaUrl;
    @Column(length=4000) public String message;
    @Column(length=12000) public String error;
    public int progress;
    @Column(nullable=false) public Instant createdAt;
    @Column(nullable=false) public Instant updatedAt;
}
