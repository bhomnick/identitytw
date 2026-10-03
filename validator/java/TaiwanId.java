import java.util.Locale;

/**
 * Taiwan ID number validator.
 *
 * Accepts ROC national ID numbers, legacy ARC/APRC numbers (two leading
 * letters, issued before 2021) and new-format ARC/APRC numbers (letter + 8/9,
 * issued from 2021).
 *
 * Format: 1 letter, then 1/2 (citizen), A-D (legacy ARC) or 8/9 (new ARC),
 * then 7 digits and a check digit.
 */
public final class TaiwanId {

    private static final String ID_PATTERN = "[A-Z][12A-D89][0-9]{8}";
    private static final String LETTER_CODES = "ABCDEFGHJKLMNPQRSTUVXYWZIO"; // index + 10 = the letter's numeric code

    private TaiwanId() {}

    public static boolean isValid(String idNumber) {
        if (idNumber == null) {
            return false;
        }
        String normalized = idNumber.toUpperCase(Locale.ROOT);
        if (!normalized.matches(ID_PATTERN)) {
            return false;
        }

        int letterCode = LETTER_CODES.indexOf(normalized.charAt(0)) + 10;
        int sum = letterCode / 10 + (letterCode % 10) * 9;

        // A letter in the second position (legacy ARC) counts as the last digit of its code.
        char second = normalized.charAt(1);
        int secondValue = Character.isLetter(second)
            ? (LETTER_CODES.indexOf(second) + 10) % 10
            : second - '0';
        sum += secondValue * 8;

        for (int i = 2; i < 9; i++) {
            sum += (9 - i) * (normalized.charAt(i) - '0');
        }
        sum += normalized.charAt(9) - '0';

        return sum % 10 == 0;
    }
}
