package kr.co.farmerflood.trigger.persistence;
import java.util.List;import org.springframework.data.jpa.repository.JpaRepository;
public interface AuthSessionJpaRepository extends JpaRepository<AuthSessionEntity,String>{List<AuthSessionEntity> findByUserId(String userId);void deleteByUserId(String userId);}
