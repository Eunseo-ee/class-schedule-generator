package schedule.domain.course;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Pattern;
import java.util.regex.Matcher;

public class CourseTimeParser {
    public record SlotSpec(Weekday day, int startSlot, int endSlot) {}
    public record ParseResult(String status, List<SlotSpec> slots) {}

    private static final Pattern SLOT =
    Pattern.compile("([월화수목금토일])\\(\\s*(\\d+)\\s*(?:~\\s*(\\d+)\\s*)?\\)");

    public static ParseResult parse(String timeRaw) {
        if (timeRaw == null || timeRaw.isBlank()) {
            return new ParseResult("no_time", List.of());
        }

        List<SlotSpec> result = new ArrayList<>();

        for (String part : timeRaw.split(",")) {
            Matcher m = SLOT.matcher(part.trim());

            if (!m.matches()) {
                return new ParseResult("parse_error", List.of());
            }

            int start = Integer.parseInt(m.group(2));
            int end = (m.group(3) == null) ? start : Integer.parseInt(m.group(3));

            if (start > end) {
                return new ParseResult("parse_error", List.of());
            }
            result.add(new SlotSpec(toDay(m.group(1)), start, end));
        }

        return new ParseResult("parsed", result);
    }

    private static Weekday toDay(String s) {
        return switch (s) {
            case "월" -> Weekday.MON;
            case "화" -> Weekday.TUE;
            case "수" -> Weekday.WED;
            case "목" -> Weekday.THU;
            case "금" -> Weekday.FRI;
            case "토" -> Weekday.SAT;
            default -> Weekday.SUN;
        };
    }
}
