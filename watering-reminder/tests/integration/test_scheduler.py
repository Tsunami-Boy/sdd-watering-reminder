from datetime import date

import pytest

from tests.fakes import FakeClock, FakeNotifier, utc
from waterbot.scheduler import tick

SANTIAGO = "America/Santiago"  # UTC-3 in January (08:00 local = 11:00 UTC)
LA_PAZ = "America/La_Paz"  # UTC-4 all year (08:00 local = 12:00 UTC)


async def setup_plant(repo, chat=1, zone=SANTIAGO, name="Catalina", last=date(2026, 1, 10), s=7):
    await repo.ensure_user(chat, utc(2026, 1, 1))
    if zone:
        await repo.set_timezone(chat, zone)
    return await repo.add_plant(chat, name, "Dólar", s, 14, last, utc(2026, 1, 1))


async def test_one_message_at_eight_local(fake_repo, notifier):
    plant = await setup_plant(fake_repo)  # watered 10 Jan, summer 7 -> due 17 Jan
    clock = FakeClock(utc(2026, 1, 17, 10, 59))
    await tick(fake_repo, notifier, clock)
    assert notifier.sent == []
    clock.set(utc(2026, 1, 17, 11, 0))
    await tick(fake_repo, notifier, clock)
    assert [(s.chat_id, s.plant_name, s.repeat) for s in notifier.sent] == [(1, "Catalina", False)]
    assert (await fake_repo.get_reminder(plant.id)).send_count == 1


async def test_second_tick_does_not_resend(fake_repo, notifier):
    await setup_plant(fake_repo)
    clock = FakeClock(utc(2026, 1, 17, 11, 0))
    await tick(fake_repo, notifier, clock)
    clock.advance(minutes=1)
    await tick(fake_repo, notifier, clock)
    assert len(notifier.sent) == 1


async def test_two_due_plants_get_one_message_each(fake_repo, notifier):
    await setup_plant(fake_repo, name="A")
    await setup_plant(fake_repo, name="B")
    await tick(fake_repo, notifier, FakeClock(utc(2026, 1, 17, 11, 0)))
    assert sorted(s.plant_name for s in notifier.sent) == ["A", "B"]


async def test_not_yet_due_and_user_without_zone_get_nothing(fake_repo, notifier):
    await setup_plant(fake_repo, chat=1, last=date(2026, 1, 12))  # due 19 Jan
    await setup_plant(fake_repo, chat=2, zone=None)
    await tick(fake_repo, notifier, FakeClock(utc(2026, 1, 17, 15, 0)))
    assert notifier.sent == []


async def test_same_moment_is_eight_for_one_zone_and_not_the_other(fake_repo, notifier):
    await setup_plant(fake_repo, chat=1, zone=SANTIAGO, name="S")
    await setup_plant(fake_repo, chat=2, zone=LA_PAZ, name="P")
    clock = FakeClock(utc(2026, 1, 17, 11, 0))  # 08:00 Santiago, 07:00 La Paz
    await tick(fake_repo, notifier, clock)
    assert [s.plant_name for s in notifier.sent] == ["S"]
    clock.set(utc(2026, 1, 17, 12, 0))  # 08:00 La Paz
    await tick(fake_repo, notifier, clock)
    assert [s.plant_name for s in notifier.sent] == ["S", "P"]


async def test_failed_send_is_retried_and_logged(fake_repo, notifier, caplog):
    plant = await setup_plant(fake_repo)
    notifier.fail_next = 1
    clock = FakeClock(utc(2026, 1, 17, 11, 0))
    with caplog.at_level("ERROR"):
        await tick(fake_repo, notifier, clock)
    assert notifier.sent == []
    assert "failed to send reminder" in caplog.text
    assert (await fake_repo.get_reminder(plant.id)).send_count == 0  # nothing recorded

    clock.advance(minutes=1)
    await tick(fake_repo, notifier, clock)  # lease still running: not retried yet
    assert notifier.sent == []
    clock.advance(minutes=2)
    await tick(fake_repo, notifier, clock)  # lease expired: retried
    assert len(notifier.sent) == 1


async def test_reminder_missed_while_offline_is_sent_once_on_recovery(fake_repo, notifier):
    await setup_plant(fake_repo)
    await tick(fake_repo, notifier, FakeClock(utc(2026, 1, 17, 10, 0)))  # before 08:00
    # bot is down at 08:00 (11:00 UTC) and comes back at 10:00 local
    await tick(fake_repo, notifier, FakeClock(utc(2026, 1, 17, 13, 0)))
    assert len(notifier.sent) == 1


async def test_overdue_plant_found_at_night_waits_until_morning(fake_repo, notifier):
    await setup_plant(fake_repo)
    clock = FakeClock(utc(2026, 1, 18, 2, 30))  # 23:30 local on the 17th
    await tick(fake_repo, notifier, clock)
    assert notifier.sent == []
    clock.set(utc(2026, 1, 18, 11, 0))
    await tick(fake_repo, notifier, clock)
    assert len(notifier.sent) == 1


@pytest.mark.parametrize("n", [1])
async def test_reminders_survive_a_new_scheduler_state(fake_repo, notifier, n):
    # Nothing is kept in memory between ticks: only the repository holds state.
    await setup_plant(fake_repo)
    await tick(fake_repo, notifier, FakeClock(utc(2026, 1, 17, 11, 0)))
    other = FakeNotifier()
    await tick(fake_repo, other, FakeClock(utc(2026, 1, 17, 11, 1)))
    assert len(notifier.sent) == n and other.sent == []
