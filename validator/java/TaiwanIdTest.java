import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

/** Runs TaiwanId against the shared fixture file. Usage: java TaiwanIdTest ../fixtures.txt */
public final class TaiwanIdTest {

    private static int count = 0;
    private static int failures = 0;

    private static void check(String id, boolean expected) {
        count++;
        if (TaiwanId.isValid(id) != expected) {
            failures++;
            System.err.println("FAIL: \"" + id + "\" should be " + (expected ? "valid" : "invalid"));
        }
    }

    public static void main(String[] args) throws Exception {
        Path fixtures = Paths.get(args.length > 0 ? args[0] : "../fixtures.txt");
        for (String raw : Files.readAllLines(fixtures)) {
            String line = raw.trim();
            if (line.isEmpty() || line.startsWith("#")) {
                continue;
            }
            String[] parts = line.split("\\s+");
            if (parts.length != 2) {
                System.err.println("Malformed fixture line: " + line);
                System.exit(1);
            }
            check(parts[1], parts[0].equals("valid"));
        }

        // Lower-case input is accepted.
        check("a123456789", true);
        check("ab12345677", true);
        check("i123456781", true); // under a Turkish locale, toUpperCase() without Locale.ROOT turns i into İ
        // Surrounding whitespace, empty and null input are rejected.
        check(" A123456789", false);
        check("A123456789 ", false);
        check("A123456789\n", false);
        check("A 23456789", false);
        check("", false);
        check(null, false);

        if (count < 20) {
            System.err.println("Too few cases ran; is fixtures.txt missing?");
            System.exit(1);
        }
        if (failures > 0) {
            System.err.println(failures + " of " + count + " cases failed");
            System.exit(1);
        }
        System.out.println("java: " + count + " cases passed");
    }
}
