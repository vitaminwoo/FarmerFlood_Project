package kr.co.farmerflood.trigger.persistence;
import org.springframework.data.jpa.repository.JpaRepository;
public interface AppUserJpaRepository extends JpaRepository<AppUserEntity,String> {boolean existsByEmail(String email);boolean existsByPhone(String phone);java.util.Optional<AppUserEntity> findByNameAndPhone(String name,String phone);java.util.Optional<AppUserEntity> findByNameAndTargetFarmerId(String name,String targetFarmerId);java.util.List<AppUserEntity> findByTargetFarmerId(String targetFarmerId);}
