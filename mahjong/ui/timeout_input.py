"""Timeout-aware stdin input using select.select() with real-time countdown."""

import sys
import time
from typing import Optional


def _timer_text(deadline: float, base_end: Optional[float]) -> str:
    """Generate timer line text showing base/bank phase."""
    from mahjong.ui.i18n import t
    now = time.monotonic()
    if base_end is not None and base_end > now:
        base_rem = int(base_end - now)
        bank_rem = int(deadline - base_end)
        return t('tc.countdown_base', base=base_rem, bank=bank_rem)
    else:
        total_rem = max(0, int(deadline - now))
        return t('tc.countdown_bank', bank=total_rem)


def _update_timer(deadline: float, base_end: Optional[float]) -> None:
    """Overwrite the timer line one row above the cursor using ANSI codes."""
    text = _timer_text(deadline, base_end)
    # Save cursor → move up 1 line → clear line → write text → restore cursor
    sys.stdout.write('\033[s\033[A\r\033[2K' + text + '\033[u')
    sys.stdout.flush()


def timed_input(prompt: str, deadline: Optional[float],
                base_end: Optional[float] = None) -> Optional[str]:
    """Read a line from stdin with an optional deadline.

    Args:
        prompt: Text to display before waiting for input.
        deadline: Absolute monotonic timestamp (time.monotonic()) after which
                  the call times out.  None means no timeout (blocks forever).
        base_end: Absolute monotonic timestamp when base time expires and bank
                  time begins.  None means no base/bank distinction.

    Returns:
        The stripped input string, or None if the deadline was reached.
    """
    if deadline is None:
        return input(prompt)

    remaining = deadline - time.monotonic()
    if remaining <= 0:
        sys.stdout.write('\n')
        sys.stdout.flush()
        return None

    _is_tty = sys.stdout.isatty()

    # Print timer line above prompt (only in TTY)
    if _is_tty:
        sys.stdout.write(_timer_text(deadline, base_end) + '\n')

    sys.stdout.write(prompt)
    sys.stdout.flush()

    try:
        import select as _sel
    except ImportError:
        # Fallback for environments without select (e.g. Windows stdin pipes)
        line = sys.stdin.readline()
        return line.rstrip('\n').strip() if line else None

    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            _flush_stdin()
            sys.stdout.write('\n')
            sys.stdout.flush()
            return None

        try:
            ready, _, _ = _sel.select([sys.stdin], [], [], min(1.0, remaining))
        except OSError:
            line = sys.stdin.readline()
            return line.rstrip('\n').strip() if line else None

        if ready:
            return sys.stdin.readline().rstrip('\n').strip()

        # 1s poll expired — update timer line if in TTY
        if _is_tty and deadline - time.monotonic() > 0:
            _update_timer(deadline, base_end)


def _flush_stdin() -> None:
    """Discard any partial input the user typed but didn't submit."""
    try:
        import termios
        termios.tcflush(sys.stdin, termios.TCIFLUSH)
    except Exception:
        pass  # Non-TTY (pytest) or Windows — silently ignore
