package br.com.banco.spider.infrastructure.persistence.jpa.repository;

import br.com.banco.spider.infrastructure.persistence.jpa.entity.MonitorProjectionEntity;
import java.time.Instant;
import java.util.List;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface MonitorProjectionJpaRepository extends JpaRepository<MonitorProjectionEntity, String> {

  @Query(
      """
      select r from MonitorProjectionEntity r
      where r.retentionUntil > :now
        and (:kind is null or r.kind = :kind)
        and (:origin is null or lower(r.origin) = lower(:origin) or lower(r.satelliteId) = lower(:origin))
        and (:query is null
          or lower(r.recordId) like :query
          or lower(coalesce(r.messageId, '')) like :query
          or lower(coalesce(r.correlationId, '')) like :query
          or lower(coalesce(r.satelliteId, '')) like :query
          or lower(coalesce(r.companyId, '')) like :query
          or lower(coalesce(r.externalRef, '')) like :query
          or lower(coalesce(r.objective, '')) like :query
          or lower(coalesce(r.eventKey, '')) like :query)
        and (:cursorUpdatedAt is null
          or r.updatedAt < :cursorUpdatedAt
          or (r.updatedAt = :cursorUpdatedAt and r.recordId < :cursorId))
      order by r.updatedAt desc, r.recordId desc
      """)
  List<MonitorProjectionEntity> search(
      @Param("now") Instant now,
      @Param("kind") String kind,
      @Param("origin") String origin,
      @Param("query") String query,
      @Param("cursorUpdatedAt") Instant cursorUpdatedAt,
      @Param("cursorId") String cursorId,
      Pageable pageable);

  @Modifying
  @Query("delete from MonitorProjectionEntity r where r.retentionUntil <= :now")
  int purgeExpired(@Param("now") Instant now);
}
