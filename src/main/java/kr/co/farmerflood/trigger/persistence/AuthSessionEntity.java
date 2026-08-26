package kr.co.farmerflood.trigger.persistence;
import jakarta.persistence.*;import java.time.Instant;
@Entity @Table(name="auth_session") public class AuthSessionEntity {@Id public String token;@Column(nullable=false)public String userId;@Column(nullable=false)public Instant createdAt;@Column(nullable=false)public Instant expiresAt;}
