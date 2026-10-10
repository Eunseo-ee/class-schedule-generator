package schedule.domain.course;

import jakarta.persistence.*;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;


@Entity
@Table(name = "course")
public class Course {
    
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "academic_year", nullable = false)
    private Short academicYear;                    // SMALLINT

    @JdbcTypeCode(SqlTypes.TINYINT)
    @Column(nullable = false)
    private Integer semester;                      // TINYINT

    @Column(name = "subj_cd", nullable = false, length = 10)
    private String subjCd;

    @Column(name = "lect_numb", nullable = false, length = 10)
    private String lectNumb;

    @Column(nullable = false, length = 200)
    private String name;

    @Column(length = 200)
    private String professor;

    @JdbcTypeCode(SqlTypes.TINYINT)
    @Column(nullable = false)
    private Integer credits;                       // TINYINT UNSIGNED

    @Column(nullable = false, length = 10)
    private String category;

    @Column(nullable = false, length = 100)
    private String department;

    @JdbcTypeCode(SqlTypes.SMALLINT)
    @Column(nullable = false)
    private Integer capacity;                      // SMALLINT UNSIGNED

    private String room;

    @Column(name = "day_night", nullable = false, length = 10)
    private String dayNight;

    @Column(nullable = false, length = 20)
    private String language;

    @Column(columnDefinition = "TEXT")
    private String note;

    @Column(name = "time_raw")
    private String timeRaw;

    @Column(name = "time_status", nullable = false, length = 20)
    private String timeStatus;

    // mappedBy: 읽기 전용 거울. FK의 주인은 CourseTimeSlot.course
    @OneToMany(mappedBy = "course", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<CourseTimeSlot> slots = new ArrayList<>();

    protected Course() {}   // JPA 전용

    public Course(Short academicYear, Integer semester, String subjCd, String lectNumb,
                  String name, String professor, Integer credits, String category,
                  String department, Integer capacity, String room, String dayNight,
                  String language, String note, String timeRaw, String timeStatus) {
        this.academicYear = academicYear;
        this.semester = semester;
        this.subjCd = subjCd;
        this.lectNumb = lectNumb;
        this.name = name;
        this.professor = professor;
        this.credits = credits;
        this.category = category;
        this.department = department;
        this.capacity = capacity;
        this.room = room;
        this.dayNight = dayNight;
        this.language = language;
        this.note = note;
        this.timeRaw = timeRaw;
        this.timeStatus = timeStatus;
    }

    // 슬롯을 붙이는 유일한 입구. 양쪽 참조를 항상 같이 세팅한다.
    public void addSlot(CourseTimeSlot slot) {
        slots.add(slot);
        slot.assignCourse(this);
    }

    public Long getId() { return id; }
    public String getName() { return name; }
    public List<CourseTimeSlot> getSlots() { return Collections.unmodifiableList(slots); }


}
