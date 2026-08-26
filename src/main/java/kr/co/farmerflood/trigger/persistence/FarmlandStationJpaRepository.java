package kr.co.farmerflood.trigger.persistence;
import java.util.List;import org.springframework.data.jpa.repository.JpaRepository;
public interface FarmlandStationJpaRepository extends JpaRepository<FarmlandStationEntity,String>{List<FarmlandStationEntity> findByFarmlandIdOrderByPriorityOrder(String farmlandId);List<FarmlandStationEntity> findByActiveTrueAndPriorityOrder(int priorityOrder);void deleteByFarmlandId(String farmlandId);}
