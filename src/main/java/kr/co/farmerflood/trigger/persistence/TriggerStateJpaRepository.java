package kr.co.farmerflood.trigger.persistence;

import org.springframework.data.jpa.repository.JpaRepository;

public interface TriggerStateJpaRepository extends JpaRepository<TriggerStateEntity,String> {}
