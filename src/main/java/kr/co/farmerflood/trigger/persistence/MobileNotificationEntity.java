package kr.co.farmerflood.trigger.persistence;
import jakarta.persistence.*;import java.time.Instant;
@Entity @Table(name="mobile_notification",uniqueConstraints=@UniqueConstraint(columnNames={"userId","alertId"}))
public class MobileNotificationEntity {@Id public String id;@Column(nullable=false)public String userId;@Column(nullable=false)public String alertId;@Column(nullable=false)public String title;@Column(nullable=false,length=1000)public String body;@Column(nullable=false)public String mediaUrl;@Column(nullable=false)public Instant createdAt;public Instant readAt;}
