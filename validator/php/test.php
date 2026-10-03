<?php
declare(strict_types=1);

require __DIR__ . '/TaiwanId.php';

$count = 0;
$failures = 0;

function check(string $id, bool $expected): void
{
    global $count, $failures;
    $count++;
    if (isValid($id) !== $expected) {
        $failures++;
        fwrite(STDERR, sprintf("FAIL: %s should be %s\n", json_encode($id), $expected ? 'valid' : 'invalid'));
    }
}

foreach (file(__DIR__ . '/../fixtures.txt') as $line) {
    $line = trim($line);
    if ($line === '' || $line[0] === '#') {
        continue;
    }
    $parts = preg_split('/\s+/', $line);
    if (count($parts) !== 2) {
        fwrite(STDERR, "Malformed fixture line: $line\n");
        exit(1);
    }
    [$expected, $id] = $parts;
    check($id, $expected === 'valid');
}

// Lower-case input is accepted.
check('a123456789', true);
check('ab12345677', true);
// Surrounding whitespace, empty input are rejected.
check(' A123456789', false);
check('A123456789 ', false);
check("A123456789\n", false);
check('A 23456789', false);
check('', false);

if ($count < 20) {
    fwrite(STDERR, "Too few cases ran; is fixtures.txt missing?\n");
    exit(1);
}
if ($failures > 0) {
    fwrite(STDERR, "$failures of $count cases failed\n");
    exit(1);
}
echo "php: $count cases passed\n";
