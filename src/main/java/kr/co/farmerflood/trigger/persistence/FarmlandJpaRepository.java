package kr.co.farmerflood.trigger.persistence;
import java.util.List;import org.springframework.data.jpa.repository.JpaRepository;
public interface FarmlandJpaRepository extends JpaRepository<FarmlandEntity,String>{List<FarmlandEntity> findByUserIdOrderByCreatedAtDesc(String userId);List<FarmlandEntity> findByActiveTrue();List<FarmlandEntity> findByActiveTrueAndDistrictAndLocality(String district,String locality);}
