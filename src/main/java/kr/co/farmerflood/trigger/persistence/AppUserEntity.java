package kr.co.farmerflood.trigger.persistence;

import jakarta.persistence.*;
import java.time.Instant;

@Entity @Table(name="app_user",uniqueConstraints={@UniqueConstraint(columnNames="email"),@UniqueConstraint(columnNames="phone")})
public class AppUserEntity {
    @Id public String id;
    @Column(nullable=false) public String email;
    @Column(nullable=false) public String name;
    public String phone;
    public String role;
    public String targetFarmerId;
    @Column(nullable=false) public Instant createdAt;
}
