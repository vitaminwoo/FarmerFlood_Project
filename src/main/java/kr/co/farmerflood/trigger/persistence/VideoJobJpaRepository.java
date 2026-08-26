package kr.co.farmerflood.trigger.persistence;

import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface VideoJobJpaRepository extends JpaRepository<VideoJobEntity,String> {
    List<VideoJobEntity> findAllByOrderByCreatedAtDesc();
    List<VideoJobEntity> findByStatusNotIn(List<String> statuses);
}
