package schedule;

import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.Test;

import schedule.domain.course.CourseTimeParser;
import schedule.domain.course.Weekday;

public class CourseTimeParserTest {
    @Test
    void 정상_케이스() {
        var r = CourseTimeParser.parse("수(3 ~ 4)");
        assertEquals("parsed", r.status());
        assertEquals(1, r.slots().size());
        assertEquals(Weekday.WED, r.slots().get(0).day());
        assertEquals(3, r.slots().get(0).startSlot());
        assertEquals(4, r.slots().get(0).endSlot());
    }

    @Test
    void 공백만_있으면_no_time() {
        var r = CourseTimeParser.parse("  ");
        assertEquals("no_time", r.status());
        assertEquals(0, r.slots().size());
    }

    @Test
    void 비어있으면_no_time() {
        var r = CourseTimeParser.parse("");
        assertEquals("no_time", r.status());
        assertEquals(0, r.slots().size());
    }

    @Test
    void null이면_no_time() {
        var r = CourseTimeParser.parse(null);
        assertEquals("no_time", r.status());
        assertEquals(0, r.slots().size());
    }

    @Test
    void 형식_오류는_parse_error() {
        var r = CourseTimeParser.parse("목(abc)");
        assertEquals("parse_error", r.status());
        assertEquals(0, r.slots().size());
    }

    @Test
    void 일부만_실패해도_전체_parse_error() {
        var r = CourseTimeParser.parse("수(3 ~ 4), 금(5 ~ 3)");
        assertEquals("parse_error", r.status());
        assertEquals(0, r.slots().size());
    }

    @Test
    void 요일_둘_범위와_단일() {
        var r = CourseTimeParser.parse("수(3 ~ 4), 목(3)");
        assertEquals(Weekday.WED, r.slots().get(0).day());
        assertEquals(3, r.slots().get(0).startSlot());
        assertEquals(4, r.slots().get(0).endSlot());
        assertEquals(Weekday.THU, r.slots().get(1).day());
        assertEquals(3, r.slots().get(1).startSlot());
        assertEquals(3, r.slots().get(1).endSlot());
    }
}