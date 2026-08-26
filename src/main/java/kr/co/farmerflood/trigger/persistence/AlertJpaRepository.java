package kr.co.farmerflood.trigger.persistence;

import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface AlertJpaRepository extends JpaRepository<AlertEntity,String> {
    List<AlertEntity> findAllByOrderByTriggeredAtDesc();
    List<AlertEntity> findByUserId(String userId);
}
