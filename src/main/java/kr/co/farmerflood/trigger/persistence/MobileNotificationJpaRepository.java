package kr.co.farmerflood.trigger.persistence;
import java.util.List;import org.springframework.data.jpa.repository.JpaRepository;
public interface MobileNotificationJpaRepository extends JpaRepository<MobileNotificationEntity,String>{List<MobileNotificationEntity> findByUserIdOrderByCreatedAtDesc(String userId);boolean existsByUserIdAndAlertId(String userId,String alertId);void deleteByUserId(String userId);}
