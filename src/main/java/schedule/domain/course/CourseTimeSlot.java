package schedule.domain.course;

import jakarta.persistence.*;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "course_time_slot")
public class CourseTimeSlot {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    // 연관관계의 주인: FK 컬럼 course_id를 실제로 관리
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "course_id", nullable = false)
    private Course course;

    @Enumerated(EnumType.STRING)
    @JdbcTypeCode(SqlTypes.VARCHAR)
    @Column(name = "day_of_week", nullable = false, length = 3)
    private Weekday dayOfWeek;

    @JdbcTypeCode(SqlTypes.TINYINT)
    @Column(name = "start_slot", nullable = false)
    private Integer startSlot;

    @JdbcTypeCode(SqlTypes.TINYINT)
    @Column(name = "end_slot", nullable = false)
    private Integer endSlot;

    protected CourseTimeSlot() {}

    public CourseTimeSlot(Weekday dayOfWeek, Integer startSlot, Integer endSlot) {
        this.dayOfWeek = dayOfWeek;
        this.startSlot = startSlot;
        this.endSlot = endSlot;
    }

    // package-private: 같은 패키지의 Course.addSlot()만 호출할 수 있다
    void assignCourse(Course course) { this.course = course; }

    public Weekday getDayOfWeek() { return dayOfWeek; }
    public Integer getStartSlot() { return startSlot; }
    public Integer getEndSlot() { return endSlot; }
}