<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { Bell, Plus, Pencil, Trash2, X } from '@lucide/svelte';

  import {
    apiRequest,
    dueLabel,
    intervalLabel,
    reminderStatusLabel,
    reminderTiming,
    type Schedule,
    type Vehicle
  } from '../../lib/api';

  type Basis = 'mileage' | 'time';
  type Entry = Schedule & { vehicle: Vehicle };

  let entries = $state<Entry[]>([]);
  let vehicles = $state<Vehicle[]>([]);
  let loading = $state(true);
  let saving = $state(false);
  let error = $state('');
  let formError = $state('');

  let selectedVehicle = $state('all');
  let statusFilter = $state('all');
  let showForm = $state(false);
  let editingId = $state<number | null>(null);

  let formVehicleId = $state('');
  let serviceType = $state('');
  let basis = $state<Basis>('mileage');
  let intervalMiles = $state<number | undefined>(undefined);
  let intervalDays = $state<number | undefined>(undefined);
  let dueMileage = $state<number | undefined>(undefined);
  let dueDate = $state('');
  let notes = $state('');

  let filtered = $derived(
    entries.filter((entry) => {
      const vehicleOk = selectedVehicle === 'all'
        || String(entry.vehicle_id) === selectedVehicle;
      const statusOk = statusFilter === 'all'
        || entry.status === statusFilter;
      return vehicleOk && statusOk;
    })
  );

  let counts = $derived({
    overdue: filtered.filter((entry) => entry.status === 'overdue').length,
    soon: filtered.filter((entry) => entry.status === 'approaching').length,
    upcoming: filtered.filter((entry) => entry.status === 'upcoming').length
  });

  async function load() {
    try {
      vehicles = await apiRequest<Vehicle[]>('/vehicles');
      const schedules = await apiRequest<Schedule[]>('/reminders');
      const byId = new Map(vehicles.map((vehicle) => [vehicle.id, vehicle]));

      entries = schedules.flatMap((schedule) => {
        const vehicle = byId.get(schedule.vehicle_id);
        return vehicle ? [{ ...schedule, vehicle }] : [];
      });

      error = '';
    } catch (err) {
      if (
        err instanceof Error &&
        /401|not authenticated|unauthorized/i.test(err.message)
      ) {
        await goto('/login');
      } else {
        error = err instanceof Error
          ? err.message
          : 'Could not load reminders';
      }
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    void load();
  });

  function openAdd() {
    editingId = null;
    formVehicleId = selectedVehicle !== 'all'
      ? selectedVehicle
      : String(vehicles[0]?.id ?? '');
    serviceType = '';
    basis = 'mileage';
    intervalMiles = undefined;
    intervalDays = undefined;
    dueMileage = undefined;
    dueDate = '';
    notes = '';
    formError = '';
    showForm = true;
  }

  function openEdit(entry: Entry) {
    editingId = entry.id;
    formVehicleId = String(entry.vehicle_id);
    serviceType = entry.service_type;
    basis = entry.interval_days != null ? 'time' : 'mileage';
    intervalMiles = entry.interval_miles ?? undefined;
    intervalDays = entry.interval_days ?? undefined;
    dueMileage = entry.due_mileage ?? undefined;
    dueDate = entry.due_date?.slice(0, 10) ?? '';
    notes = entry.notes ?? '';
    formError = '';
    showForm = true;
  }

  function payload() {
    const shared = {
      service_type: serviceType.trim(),
      notes: notes.trim() || null
    };

    if (basis === 'mileage') {
      return {
        ...shared,
        interval_miles: Number(intervalMiles),
        due_mileage: Number(dueMileage),
        interval_days: null,
        due_date: null
      };
    }

    return {
      ...shared,
      interval_days: Number(intervalDays),
      due_date: dueDate,
      interval_miles: null,
      due_mileage: null
    };
  }

  function formIsValid(): boolean {
    if (!formVehicleId || !serviceType.trim()) {
      formError = 'Enter a service type and select a vehicle.';
      return false;
    }

    if (basis === 'mileage') {
      if (
        intervalMiles == null ||
        !Number.isFinite(intervalMiles) ||
        intervalMiles < 1 ||
        dueMileage == null ||
        !Number.isFinite(dueMileage) ||
        dueMileage < 0
      ) {
        formError = 'Enter a mileage interval of at least 1 and a due mileage of 0 or more.';
        return false;
      }
      return true;
    }

    if (
      intervalDays == null ||
      !Number.isFinite(intervalDays) ||
      intervalDays < 1 ||
      !dueDate
    ) {
      formError = 'Enter a time interval of at least 1 day and a due date.';
      return false;
    }

    return true;
  }

  async function saveSchedule(event: SubmitEvent) {
    event.preventDefault();
    if (!formIsValid()) return;

    saving = true;
    formError = '';

    try {
      const endpoint = editingId === null
        ? `/vehicles/${formVehicleId}/schedules`
        : `/schedules/${editingId}`;

      await apiRequest(endpoint, {
        method: editingId === null ? 'POST' : 'PUT',
        body: JSON.stringify(payload())
      });

      showForm = false;
      await load();
    } catch (err) {
      formError = err instanceof Error
        ? err.message
        : 'Could not save reminder';
    } finally {
      saving = false;
    }
  }

  async function deleteSchedule(entry: Entry) {
    const confirmed = confirm(
      `Delete the ${entry.service_type} reminder for ${entry.vehicle.make} ${entry.vehicle.model}?`
    );

    if (!confirmed) return;

    try {
      await apiRequest(`/schedules/${entry.id}`, {
        method: 'DELETE'
      });

      await load();
    } catch (err) {
      error = err instanceof Error
        ? err.message
        : 'Could not delete reminder';
    }
  }
</script>

<svelte:head>
  <title>Reminders | PocketMechanic</title>
</svelte:head>

<div class="heading">
  <div>
    <div class="eyebrow">SERVICE SCHEDULE</div>
    <h1>Reminders</h1>
    <p>
      Schedule maintenance by mileage or by time. A service is due soon within 500 miles or 14 days, and overdue after the due mileage or date.
    </p>
  </div>

  <button
    class="primary"
    onclick={openAdd}
    disabled={loading || vehicles.length === 0}
  >
    <Plus size={20} />
    Add Reminder
  </button>
</div>

{#if error}
  <div class="alert" role="alert">{error}</div>
{/if}

<section class="counts">
  <div>
    <span>Overdue</span>
    <strong class="overdue">{counts.overdue}</strong>
  </div>
  <div>
    <span>Due soon</span>
    <strong class="soon">{counts.soon}</strong>
  </div>
  <div>
    <span>Upcoming</span>
    <strong>{counts.upcoming}</strong>
  </div>
</section>

<section class="panel">
  <div class="toolbar">
    <h2>Scheduled Services ({filtered.length})</h2>

    <div class="filters">
      <label>
        Filter by vehicle

        <select bind:value={selectedVehicle}>
          <option value="all">All Vehicles</option>

          {#each vehicles as vehicle (vehicle.id)}
            <option value={String(vehicle.id)}>
              {vehicle.year} {vehicle.make} {vehicle.model}
            </option>
          {/each}
        </select>
      </label>

      <label>
        Status

        <select bind:value={statusFilter}>
          <option value="all">All statuses</option>
          <option value="overdue">Overdue</option>
          <option value="approaching">Due soon</option>
          <option value="upcoming">Upcoming</option>
        </select>
      </label>
    </div>
  </div>

  {#if loading}
    <p class="muted">Loading reminders...</p>

  {:else if vehicles.length === 0}
    <div class="empty">
      <Bell size={48} color="#3478f6" />

      <h3>Add a vehicle first</h3>
      <p>You need a vehicle before scheduling service reminders.</p>

      <a class="primary" href="/vehicles">
        Add Vehicle
      </a>
    </div>

  {:else if entries.length === 0}
    <div class="empty">
      <Bell size={48} color="#3478f6" />

      <h3>No reminders yet</h3>
      <p>Add a schedule for the next oil change, inspection, or other service.</p>

      <button class="primary" onclick={openAdd}>
        <Plus size={20} />
        Add Reminder
      </button>
    </div>

  {:else if filtered.length === 0}
    <div class="empty">
      <Bell size={48} color="#3478f6" />

      <h3>No reminders match</h3>
      <p>Try a different vehicle or status.</p>
    </div>

  {:else}
    <div class="records">
      {#each filtered as entry (entry.id)}
        <article class="record">
          <div class="record-icon {entry.status}">
            <Bell size={24} />
          </div>

          <div class="record-body">
            <h3>
              {entry.service_type}
              <span class="badge {entry.status}">
                {reminderStatusLabel(entry.status)}
              </span>
            </h3>

            <p>
              {entry.vehicle.year}
              {entry.vehicle.make}
              {entry.vehicle.model}
            </p>

            <p>{intervalLabel(entry)}</p>

            {#if entry.notes}
              <p class="notes">{entry.notes}</p>
            {/if}
          </div>

          <div class="record-meta">
            <strong>{reminderTiming(entry)}</strong>
            <span>{dueLabel(entry)}</span>
          </div>

          <div class="record-actions">
            <button
              class="icon-button"
              title="Edit reminder"
              aria-label="Edit reminder"
              onclick={() => openEdit(entry)}
            >
              <Pencil size={19} />
            </button>

            <button
              class="icon-button danger"
              title="Delete reminder"
              aria-label="Delete reminder"
              onclick={() => deleteSchedule(entry)}
            >
              <Trash2 size={19} />
            </button>
          </div>
        </article>
      {/each}
    </div>
  {/if}
</section>

{#if showForm}
  <div
    class="overlay"
    role="presentation"
    onclick={(event) => {
      if (event.target === event.currentTarget) {
        showForm = false;
      }
    }}
  >
    <div
      class="dialog"
      role="dialog"
      aria-modal="true"
      aria-label="Reminder form"
      tabindex="-1"
    >
      <div class="dialog-heading">
        <h2>
          {editingId === null ? 'Add Reminder' : 'Edit Reminder'}
        </h2>

        <button
          class="icon-button"
          aria-label="Close"
          onclick={() => showForm = false}
        >
          <X size={22} />
        </button>
      </div>

      <form onsubmit={saveSchedule}>
        <label>
          Vehicle

          <select
            bind:value={formVehicleId}
            disabled={editingId !== null}
            required
          >
            {#each vehicles as vehicle (vehicle.id)}
              <option value={String(vehicle.id)}>
                {vehicle.year}
                {vehicle.make}
                {vehicle.model}
              </option>
            {/each}
          </select>
        </label>

        <label>
          Service Type

          <input
            bind:value={serviceType}
            placeholder="Oil Change, Inspection, Tire Rotation..."
            maxlength="100"
            required
          />
        </label>

        <fieldset>
          <legend>Remind by</legend>

          <label class="choice">
            <input type="radio" value="mileage" bind:group={basis} />
            Mileage
          </label>

          <label class="choice">
            <input type="radio" value="time" bind:group={basis} />
            Time
          </label>
        </fieldset>

        {#if basis === 'mileage'}
          <div class="two-col">
            <label>
              Every (miles)

              <input
                type="number"
                min="1"
                step="1"
                bind:value={intervalMiles}
                placeholder="5000"
                required
              />
            </label>

            <label>
              Due at mileage

              <input
                type="number"
                min="0"
                step="1"
                bind:value={dueMileage}
                placeholder="15000"
                required
              />
            </label>
          </div>
        {:else}
          <div class="two-col">
            <label>
              Every (days)

              <input
                type="number"
                min="1"
                step="1"
                bind:value={intervalDays}
                placeholder="180"
                required
              />
            </label>

            <label>
              Due date

              <input
                type="date"
                bind:value={dueDate}
                required
              />
            </label>
          </div>
        {/if}

        <label>
          Notes (optional)

          <textarea
            bind:value={notes}
            maxlength="2000"
            rows="3"
            placeholder="Additional details..."
          ></textarea>
        </label>

        <p class="hint">
          After the service is done, edit the reminder and set the next due mileage or date.
        </p>

        {#if formError}
          <p class="alert" role="alert">{formError}</p>
        {/if}

        <div class="form-actions">
          <button
            type="button"
            class="secondary"
            onclick={() => showForm = false}
          >
            Cancel
          </button>

          <button
            class="primary"
            type="submit"
            disabled={saving}
          >
            {saving ? 'Saving...' : 'Save Reminder'}
          </button>
        </div>
      </form>
    </div>
  </div>
{/if}

<style>
  .heading {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 20px;
    margin-bottom: 30px;
  }

  .eyebrow {
    font-size: 13px;
    letter-spacing: 1.5px;
    color: #3478f6;
    font-weight: 800;
    margin-bottom: 10px;
  }

  h1 {
    font-size: 33px;
    margin-bottom: 9px;
  }

  .heading p, .muted, .hint {
    color: #8794a8;
    font-size: 16px;
  }

  .hint {
    font-size: 14px;
    line-height: 1.5;
    margin-bottom: 8px;
  }

  .primary, .secondary {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 9px;
    padding: 14px 20px;
    border: 0;
    border-radius: 11px;
    font-size: 16px;
    font-weight: 700;
    cursor: pointer;
    text-decoration: none;
  }

  .primary {
    background: #3478f6;
    color: white;
  }

  .primary:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .primary:hover:not(:disabled) {
    background: #2563dc;
  }

  .secondary {
    background: #edf1f8;
    color: #24324a;
  }

  .counts {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 18px;
    margin-bottom: 24px;
  }

  .counts div {
    background: white;
    border: 1px solid #e8edf5;
    border-radius: 17px;
    padding: 22px 26px;
  }

  .counts span {
    display: block;
    color: #8794a8;
    font-size: 15px;
  }

  .counts strong {
    display: block;
    font-size: 30px;
    margin-top: 4px;
  }

  .counts .overdue {
    color: #be123c;
  }

  .counts .soon {
    color: #c2410c;
  }

  .panel {
    background: white;
    border: 1px solid #e8edf5;
    border-radius: 17px;
    padding: 28px;
  }

  .toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 15px;
    margin-bottom: 20px;
  }

  .toolbar h2 {
    font-size: 23px;
    margin: 0;
  }

  .filters {
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
  }

  .toolbar label, .choice {
    font-size: 15px;
    font-weight: 700;
    display: flex;
    align-items: center;
    gap: 10px;
  }

  select, input, textarea {
    border: 1px solid #dfe5ef;
    border-radius: 10px;
    padding: 12px;
    font: inherit;
    font-size: 16px;
    background: white;
    color: #17233b;
  }

  .record {
    display: flex;
    align-items: center;
    gap: 17px;
    padding: 22px 0;
    border-top: 1px solid #edf1f7;
  }

  .record-icon {
    width: 50px;
    height: 50px;
    border-radius: 13px;
    display: grid;
    place-items: center;
    background: #eaf1ff;
    color: #3478f6;
    flex-shrink: 0;
  }

  .record-icon.overdue {
    background: #ffe4e6;
    color: #be123c;
  }

  .record-icon.approaching {
    background: #fff4e5;
    color: #c2410c;
  }

  .record-body {
    flex: 1;
    min-width: 0;
  }

  .record-body h3 {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
    font-size: 19px;
    margin-bottom: 7px;
  }

  .record-body p, .record-meta span {
    font-size: 15px;
    color: #8794a8;
    margin: 0;
  }

  .record-body .notes {
    margin-top: 9px;
    color: #475569;
    white-space: pre-wrap;
  }

  .badge {
    display: inline-block;
    padding: 3px 8px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 800;
    background: #eaf1ff;
    color: #3478f6;
  }

  .badge.overdue {
    background: #ffe4e6;
    color: #be123c;
  }

  .badge.approaching {
    background: #fff4e5;
    color: #c2410c;
  }

  .record-meta {
    display: flex;
    flex-direction: column;
    gap: 7px;
    text-align: right;
    font-size: 15px;
  }

  .record-meta strong {
    font-size: 18px;
  }

  .record-actions {
    display: flex;
    gap: 6px;
  }

  .icon-button {
    border: 0;
    background: #f2f5fa;
    color: #59677d;
    border-radius: 9px;
    padding: 10px;
    display: grid;
    place-items: center;
    cursor: pointer;
  }

  .icon-button:hover {
    background: #e3eaf5;
  }

  .danger {
    color: #d83e49;
  }

  .empty {
    text-align: center;
    padding: 75px 12px;
  }

  .empty h3 {
    font-size: 22px;
    margin: 17px 0 8px;
  }

  .empty p {
    color: #8794a8;
    font-size: 16px;
    margin-bottom: 24px;
  }

  .alert {
    color: #b91c1c;
    background: #fff1f2;
    border-radius: 10px;
    padding: 13px;
    margin-bottom: 18px;
  }

  .overlay {
    position: fixed;
    inset: 0;
    background: #101a2c99;
    display: grid;
    place-items: center;
    padding: 20px;
    z-index: 30;
  }

  .dialog {
    width: min(100%, 650px);
    background: white;
    border-radius: 18px;
    padding: 32px;
    max-height: 90vh;
    overflow-y: auto;
  }

  .dialog-heading {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
  }

  .dialog-heading h2 {
    font-size: 25px;
    margin: 0;
  }

  .dialog form label, .dialog form fieldset {
    display: block;
    font-size: 15px;
    font-weight: 700;
    margin-bottom: 18px;
  }

  fieldset {
    border: 0;
    padding: 0;
  }

  legend {
    font-weight: 700;
    margin-bottom: 10px;
  }

  .choice {
    display: inline-flex;
    margin-right: 18px;
    font-weight: 600;
  }

  .choice input {
    width: auto;
    margin: 0;
  }

  .dialog form .choice {
    display: inline-flex;
    width: auto;
    margin-bottom: 0;
  }

  .dialog form input,
  .dialog form select,
  .dialog form textarea {
    display: block;
    width: 100%;
    margin-top: 9px;
    padding: 15px;
  }

  .dialog form .choice input {
    width: auto;
    margin-top: 0;
    padding: 0;
  }

  .two-col {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }

  .form-actions {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
    margin-top: 12px;
  }

  @media (max-width: 800px) {
    .counts {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 650px) {
    .heading, .toolbar {
      align-items: flex-start;
      flex-direction: column;
    }

    .record {
      flex-wrap: wrap;
    }

    .record-meta {
      text-align: left;
    }

    .dialog {
      padding: 22px;
    }

    .two-col {
      grid-template-columns: 1fr;
    }
  }
</style>
