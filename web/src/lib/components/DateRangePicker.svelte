<script lang="ts">
  interface Props {
    start_date?: Date;
    end_date?: Date;
  }

  let { start_date = $bindable(undefined), end_date = $bindable(undefined) }: Props = $props();

  let start_date_input = $state(toInputString(start_date));
  let end_date_input = $state(toInputString(end_date));

  $effect(() => {
    start_date = fromInputString(start_date_input);
  });

  $effect(() => {
    end_date = fromInputString(end_date_input);
  });

  function toInputString(date?: Date): string {
    if (!date) return "";
    const offset = date.getTimezoneOffset();
    const localDate = new Date(date.getTime() - offset * 60 * 1000);
    return localDate.toISOString().split("T")[0];
  }

  function fromInputString(dateStr: string): Date | undefined {
    if (!dateStr) return undefined;
    return new Date(dateStr + "T00:00:00");
  }
</script>

<div class="flex flex-col gap-2">
  <div
    class="flex justify-between items-center rounded-md border border-gray-300 bg-white focus-within:border-blue-500 focus-within:ring-1 focus-within:ring-blue-500"
  >
    <input
      type="date"
      class="border-none bg-transparent p-2 text-sm text-gray-900 focus:ring-0"
      bind:value={start_date_input}
    />

    <span class="px-2 text-gray-400">→</span>

    <input
      type="date"
      class="border-none bg-transparent p-2 text-sm text-gray-900 focus:ring-0"
      min={start_date_input}
      bind:value={end_date_input}
    />
  </div>
</div>