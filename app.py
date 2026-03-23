# /// script
# dependencies = [
#     "textual",
#     "psutil",
#     "pynvml",
#     "rich",
# ]
# ///

import sys
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, ProgressBar, Sparkline, Label, DataTable, TabbedContent, TabPane, Digits, ListView, ListItem
from textual.containers import Container, Vertical, Horizontal, Grid
from monitor import Monitor


def append_history(existing, value, limit=60):
    history = list(existing or [])
    history.append(value)
    return history[-limit:]


def truncate_text(value, limit):
    text = str(value)
    if len(text) <= limit:
        return text
    if limit <= 1:
        return text[:limit]
    return f"{text[:limit - 1]}…"

def get_icon(icon_type: str) -> str:
    """Returns an icon with a text fallback for compatibility."""
    icons = {
        "pass": ("✅", "OK"),
        "warn": ("⚠️", "!!"),
        "alert": ("🚨", "!!"),
    }
    # Check if the terminal likely supports Unicode (common heuristic)
    import os
    supports_unicode = "UTF-8" in os.environ.get("LANG", "").upper() or os.environ.get("TERM_PROGRAM") == "vscode"
    
    icon, fallback = icons.get(icon_type, ("", ""))
    return icon if supports_unicode else fallback

class DashboardWidget(Static):
    def compose(self) -> ComposeResult:
        with Vertical():
            with Horizontal(id="system-info-bar"):
                self.os_label = Label("OS: Loading...", classes="info-chip")
                self.uptime_label = Label("Uptime: Loading...", classes="info-chip")
                yield self.os_label
                yield self.uptime_label
            
            with Grid(id="dashboard-grid"):
                with Vertical(classes="dash-card"):
                    yield Label("Overall CPU", classes="section-title")
                    self.cpu_digits = Digits("0%")
                    self.cpu_bar = ProgressBar(total=100, show_percentage=True)
                    yield self.cpu_digits
                    yield self.cpu_bar
                
                with Vertical(classes="dash-card"):
                    yield Label("Memory Usage", classes="section-title")
                    self.mem_digits = Digits("0%")
                    self.mem_bar = ProgressBar(total=100, show_percentage=True)
                    self.mem_label = Label("0/0 GB")
                    yield self.mem_digits
                    yield self.mem_bar
                    yield self.mem_label

                with Vertical(classes="dash-card"):
                    yield Label("Network", classes="section-title")
                    self.net_down = Label("Download: 0 KB/s")
                    self.net_up = Label("Upload: 0 KB/s")
                    self.net_spark = Sparkline(id="dash-net-spark")
                    yield self.net_down
                    yield self.net_up
                    yield self.net_spark

    def update_stats(self, cpu_avg, mem_data, net_data, sys_info):
        # System Info
        os_name, uptime = sys_info
        self.os_label.update(f"OS: [bold cyan]{os_name}[/]")
        self.uptime_label.update(f"Uptime: [bold yellow]{uptime}[/]")

        # CPU - Use integer for Digits to avoid glitches with decimals/percent signs
        val_cpu = int(cpu_avg)
        self.cpu_digits.update(f"{val_cpu}%")
        self.cpu_bar.progress = cpu_avg
        
        # Memory
        percent, used, total = mem_data
        val_mem = int(percent)
        self.mem_digits.update(f"{val_mem}%")
        self.mem_bar.progress = percent
        self.mem_label.update(f"{used:.1f} / {total:.1f} GB")

        # Network
        down, up = net_data
        self.net_down.update(f"Download: [cyan]{down:.1f} KB/s[/cyan]")
        self.net_up.update(f"Upload: [magenta]{up:.1f} KB/s[/magenta]")
        self.net_spark.data = append_history(self.net_spark.data, down + up)

class CPUWidget(Static):
    def __init__(self, monitor):
        super().__init__()
        self.monitor = monitor
        self.core_count = len(self.monitor.get_cpu_stats())

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Per-Core CPU Usage", classes="section-title")
            self.bars = []
            for i in range(self.core_count):
                with Horizontal(classes="core-row"):
                    label = Label(f"Core {i:2d}", classes="core-label")
                    bar = ProgressBar(total=100, show_percentage=True, id=f"cpu-{i}")
                    # In dynamic mode, we don't hide them initially
                    self.bars.append((label, bar))
                    yield label
                    yield bar

    def update_stats(self, stats):
        for i, val in enumerate(stats):
            if i < len(self.bars):
                label, bar = self.bars[i]
                label.display = True
                bar.display = True
                bar.progress = val
                # Dynamic styling based on usage
                if val > 80:
                    bar.styles.bar_foreground = "#f7768e"
                elif val > 50:
                    bar.styles.bar_foreground = "#e0af68"
                else:
                    bar.styles.bar_foreground = "#9ece6a"

class MemoryWidget(Static):
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Detailed Memory Stats", classes="section-title")
            self.main_bar = ProgressBar(total=100, show_percentage=True)
            self.stats_label = Label("Loading...")
            yield self.main_bar
            yield self.stats_label
            yield Label("\nMemory History", classes="subtle-title")
            self.history = Sparkline()
            yield self.history

    def update_stats(self, percent, used, total):
        self.main_bar.progress = percent
        self.stats_label.update(f"Used: [bold]{used:.2f} GB[/bold] | Total: [bold]{total:.2f} GB[/bold]")
        self.history.data = append_history(self.history.data, percent)

class NetworkWidget(Static):
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Network Traffic", classes="section-title")
            with Horizontal(classes="stats-row"):
                with Vertical():
                    yield Label("Download Speed", classes="subtle-title")
                    self.download_spark = Sparkline(id="net-down", summary_function=max)
                    self.download_label = Label("0 KB/s")
                    yield self.download_spark
                    yield self.download_label
                with Vertical():
                    yield Label("Upload Speed", classes="subtle-title")
                    self.upload_spark = Sparkline(id="net-up", summary_function=max)
                    self.upload_label = Label("0 KB/s")
                    yield self.upload_spark
                    yield self.upload_label

    def update_stats(self, down, up):
        self.download_spark.data = append_history(self.download_spark.data, down)
        self.upload_spark.data = append_history(self.upload_spark.data, up)
        self.download_label.update(f"[cyan]{down:.1f} KB/s[/cyan]")
        self.upload_label.update(f"[magenta]{up:.1f} KB/s[/magenta]")

class ConnectionsWidget(Static):
    def compose(self) -> ComposeResult:
        yield Label("Active Network Connections", classes="section-title")
        self.summary = Label("Waiting for connection data...", classes="panel-summary")
        yield self.summary
        self.table = DataTable()
        self.table.add_columns("Proto", "Local Address", "Remote Address", "Status", "PID")
        yield self.table

    def update_stats(self, connections):
        self.table.clear()
        if connections and isinstance(connections[0], dict) and "error" in connections[0]:
            self.summary.update("[red]Connection discovery failed[/red]")
            self.table.add_row("-", f"[red]{connections[0]['error']}[/]", "-", "-", "-")
            return

        if not connections:
            self.summary.update("[dim]No active or listening connections detected.[/dim]")
            self.table.add_row("-", "No connections detected", "-", "-", "-")
            return

        established = sum(1 for conn in connections if conn["status"] in {"ESTABLISHED", "ESTAB"})
        listening = sum(1 for conn in connections if conn["status"] == "LISTEN")
        self.summary.update(f"{len(connections)} visible sockets | {established} established | {listening} listening")

        for conn in connections:
            status = conn['status']
            if status in {'ESTABLISHED', 'ESTAB'}:
                status_display = f"[green]{status}[/]"
            elif status == 'LISTEN':
                status_display = f"[yellow]{status}[/]"
            else:
                status_display = f"[cyan]{status}[/]"
            
            self.table.add_row(
                conn.get('proto', '-'),
                conn['laddr'],
                conn['raddr'],
                status_display,
                str(conn['pid'])
            )

class DiskWidget(Static):
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Disk I/O Activity", classes="section-title")
            with Horizontal(classes="stats-row"):
                with Vertical():
                    yield Label("Read Throughput", classes="subtle-title")
                    self.read_spark = Sparkline(id="disk-read", summary_function=max)
                    self.read_label = Label("0 KB/s")
                    yield self.read_spark
                    yield self.read_label
                with Vertical():
                    yield Label("Write Throughput", classes="subtle-title")
                    self.write_spark = Sparkline(id="disk-write", summary_function=max)
                    self.write_label = Label("0 KB/s")
                    yield self.write_spark
                    yield self.write_label

    def update_stats(self, read, write):
        self.read_spark.data = append_history(self.read_spark.data, read)
        self.write_spark.data = append_history(self.write_spark.data, write)
        self.read_label.update(f"[blue]{read:.1f} KB/s[/blue]")
        self.write_label.update(f"[orange3]{write:.1f} KB/s[/orange3]")

class DiskHealthWidget(Static):
    def compose(self) -> ComposeResult:
        yield Label("Disk S.M.A.R.T. Health Assessment", classes="section-title")
        self.summary = Label("Scanning disks...", classes="panel-summary")
        yield self.summary
        self.table = DataTable()
        yield self.table

    def on_mount(self) -> None:
        self.table.add_columns(" ", "Dev", "Model", "Type", "Status", "Temp", "Hours", "Realloc", "Note")

    def update_stats(self, disks):
        self.table.clear()
        
        # Ensure columns exist (safety check)
        if not self.table.columns:
            self.table.add_columns(" ", "Dev", "Model", "Type", "Status", "Temp", "Hours", "Realloc", "Note")

        if not disks:
            self.summary.update("[dim]No disks detected.[/dim]")
            self.table.add_row("", "No disks detected.", "-", "-", "-", "-", "-", "-", "-")
            return

        if disks and isinstance(disks[0], dict) and "error" in disks[0]:
            self.summary.update("[red]Disk health scan failed[/red]")
            self.table.add_row("!", f"[red]{disks[0]['error']}[/]", "-", "-", "-", "-", "-", "-", "-")
            return

        passing = sum(1 for disk in disks if disk["status"] == "PASSED")
        degraded = sum(1 for disk in disks if disk.get("alert"))
        self.summary.update(f"{len(disks)} disks | {passing} healthy | {degraded} needing attention")

        for disk in disks:
            if disk['status'] == "PASSED":
                status_style = "[green]"
                icon = get_icon("pass")
            elif disk['status'] == "UNAVAILABLE":
                status_style = "[yellow]"
                icon = get_icon("warn")
            else:
                status_style = "[bold red]"
                icon = get_icon("alert") if disk.get('alert') else get_icon("warn")

            reallocated = disk.get('reallocated', 'N/A')
            self.table.add_row(
                icon,
                truncate_text(disk['device'], 12),
                truncate_text(disk['model'], 22),
                truncate_text(disk.get('media', 'N/A'), 6),
                f"{status_style}{disk['status']}[/]",
                disk['temp'],
                truncate_text(disk['power_on'], 10),
                f"[bold red]{reallocated}[/]" if isinstance(reallocated, int) and reallocated > 0 else str(reallocated),
                truncate_text(disk.get('notes', '-'), 22)
            )

class GPUCard(Vertical):
    def __init__(self, name: str):
        super().__init__(classes="gpu-card")
        self.gpu_name = name

    def compose(self) -> ComposeResult:
        yield Label(f"[bold cyan]{self.gpu_name}[/bold cyan]")
        self.util_label = Label("Utilization: 0%")
        yield self.util_label
        self.spark = Sparkline()
        yield self.spark
        self.mem_label = Label("Memory: 0%")
        yield self.mem_label

    def update_stats(self, util, mem):
        # Ensure sub-widgets exist before updating (composition is async after mount)
        if not hasattr(self, "util_label"):
            return

        self.util_label.update(f"Utilization: [green]{util}%[/green]")
        self.mem_label.update(f"Memory: [yellow]{mem:.1f}%[/yellow]")
        self.spark.data = append_history(self.spark.data, util)

class GPUWidget(Static):
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("GPU Performance Tracking", classes="section-title")
            self.gpu_container = Vertical(id="gpu-container")
            yield self.gpu_container

    def on_mount(self):
        self.gpu_cards = {}

    def update_stats(self, gpus):
        if not gpus:
            if not hasattr(self, "no_gpu_label"):
                self.gpu_container.remove_children()
                self.no_gpu_label = Label("[dim]No compatible GPUs detected.[/dim]")
                self.gpu_container.mount(self.no_gpu_label)
            return
        
        if hasattr(self, "no_gpu_label"):
            self.no_gpu_label.remove()
            delattr(self, "no_gpu_label")

        for i, gpu in enumerate(gpus):
            if i not in self.gpu_cards:
                new_card = GPUCard(gpu.get('name', f"GPU {i}"))
                self.gpu_container.mount(new_card)
                self.gpu_cards[i] = new_card
            
            self.gpu_cards[i].update_stats(gpu['util'], gpu['mem'])

class ProcessWidget(Static):
    def compose(self) -> ComposeResult:
        yield Label("Top System Processes", classes="section-title")
        self.summary = Label("Sampling processes...", classes="panel-summary")
        yield self.summary
        self.table = DataTable()
        yield self.table

    def on_mount(self) -> None:
        self.table.add_columns("PID", "Name", "CPU%", "MEM%")

    def update_stats(self, processes):
        self.table.clear()
        
        if processes and isinstance(processes[0], dict) and "error" in processes[0]:
            # If columns were cleared (shouldn't happen with .clear()), add them back
            if not self.table.columns:
                self.table.add_columns("PID", "Name", "CPU%", "MEM%")
            self.summary.update("[red]Process sampling failed[/red]")
            self.table.add_row("-", f"[red]{processes[0]['error']}[/]", "-", "-")
            return

        if not processes:
            if not self.table.columns:
                self.table.add_columns("PID", "Name", "CPU%", "MEM%")
            self.summary.update("[dim]No runnable processes found.[/dim]")
            self.table.add_row("-", "No processes found", "-", "-")
            return

        busiest = processes[0]
        self.summary.update(f"{len(processes)} processes shown | top CPU: {busiest['name']} ({busiest['cpu']:.1f}%)")

        for proc in processes:
            cpu = proc['cpu']
            # Divide by CPU count for actual per-core percentage (psutil logic on some OSs)
            # But let's keep it simple for now as per monitor output
            if cpu > 50:
                cpu_display = f"[bold red]{cpu}%[/]"
            elif cpu > 20:
                cpu_display = f"[yellow]{cpu}%[/]"
            else:
                cpu_display = f"{cpu}%"
            
            self.table.add_row(
                str(proc['pid']),
                f"[bold]{proc['name']}[/]",
                cpu_display,
                f"{proc['mem']:.1f}%"
            )

class LogViewerWidget(Static):
    def __init__(self, monitor):
        super().__init__()
        self.monitor = monitor
        self.sources = []

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical(id="log-sidebar"):
                yield Label("Sources", classes="section-title")
                self.source_list = ListView(id="log-sources")
                yield self.source_list
            with Vertical(id="log-content-area"):
                yield Label("Log Entries", classes="section-title")
                self.log_text = Static("Select a log source...", id="log-text")
                yield self.log_text

    def on_mount(self) -> None:
        self.refresh_sources()

    def refresh_sources(self) -> None:
        self.sources = self.monitor.get_available_logs()
        self.source_list.clear()
        for s in self.sources:
            # Textual IDs cannot contain dots, replace them with underscores
            safe_id = s.replace(".", "_")
            self.source_list.append(ListItem(Label(s), id=f"source-{safe_id}"))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        # Get the index of the selected item from the event's list view
        index = event.list_view.index
        if index is not None and 0 <= index < len(self.sources):
            source = self.sources[index]
            content = self.monitor.get_log_content(source)
            self.log_text.update("\n".join(content))

class AboutWidget(Static):
    def compose(self) -> ComposeResult:
        yield Label("About PyTask: Linux Task Manager", classes="section-title")
        yield Static(
            "\n[bold cyan]PyTask[/bold cyan] is a modern, terminal-based system monitor.\n\n"
            "Built with [bold]Python[/bold] and the [bold]Textual[/bold] framework.\n\n"
            "Features:\n"
            " - Real-time CPU & Memory monitoring\n"
            " - Network traffic & active connections\n"
            " - Disk I/O & S.M.A.R.T. health data\n"
            " - GPU performance tracking\n"
            " - Process management\n"
            " - System log viewer\n\n"
            "Created for the [bold green]Linux[/bold green] community.\n"
            "Version: [bold yellow]1.3.1[/bold yellow]\n\n"
            "Shortcut Keys:\n"
            " [bold yellow]1-9, 0[/bold yellow]: Switch Tabs\n"
            " [bold yellow]t / T[/bold yellow]: Next / Previous Tab\n"
            " [bold yellow]Esc / q[/bold yellow]: Exit App"
        )

class TaskManagerApp(App):
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("escape", "quit", "Exit"),
        ("t", "next_tab", "Next Tab"),
        ("shift+t", "previous_tab", "Prev Tab"),
        ("1", "switch_tab(0)", "Dash"),
        ("2", "switch_tab(1)", "CPU"),
        ("3", "switch_tab(2)", "Proc"),
        ("4", "switch_tab(3)", "Mem"),
        ("5", "switch_tab(4)", "Health"),
        ("6", "switch_tab(5)", "Logs"),
        ("7", "switch_tab(6)", "Net"),
        ("8", "switch_tab(7)", "Disk"),
        ("9", "switch_tab(8)", "Conn"),
        ("g", "switch_tab(9)", "GPU"),
        ("0", "switch_tab(10)", "About"),
    ]
    CSS = """
    Screen {
        background: #0b1220;
        color: #d9e4f5;
    }
    Header {
        background: #111a2b;
        color: #f5f7fb;
        border-bottom: solid #30415f;
    }
    Footer {
        background: #111a2b;
        color: #c3d3ea;
        border-top: solid #30415f;
        height: 1;
        dock: bottom;
    }
    Footer > .footer--key {
        color: #8bd5ca;
        background: #111a2b;
    }
    Footer > .footer--description {
        color: #c3d3ea;
    }
    Footer > .footer--highlight {
        background: #1f314f;
    }
    #system-info-bar {
        height: 3;
        border: round #30415f;
        padding: 0 1;
        background: #111a2b;
        align: center middle;
        margin-bottom: 1;
    }
    .info-chip {
        margin: 0 2;
        padding: 0 1;
        background: #18243a;
        color: #d9e4f5;
    }
    TabbedContent {
        background: #0b1220;
    }
    Tabs {
        background: #0b1220;
        border-bottom: solid #30415f;
    }
    Tab {
        color: #c3d3ea;
        background: #111a2b;
        margin-right: 1;
    }
    Tab:focus {
        background: #1c2a42;
    }
    Tab.-active {
        color: #f5f7fb;
        background: #263754;
    }
    TabPane {
        padding: 1 2;
        background: #0f1728;
        border: round #30415f;
        margin: 1;
    }
    Label {
        color: #d9e4f5;
        text-style: bold;
        margin-bottom: 1;
    }
    Static {
        color: #d9e4f5;
    }
    .section-title {
        color: #8bd5ca;
    }
    .subtle-title {
        color: #8aa5c5;
    }
    .panel-summary {
        color: #8aa5c5;
    }
    #dashboard-grid {
        grid-size: 3 1;
        grid-gutter: 2;
        height: 16;
    }
    .dash-card {
        border: round #30415f;
        padding: 1 2;
        background: #111a2b;
        align: center middle;
        text-align: center;
    }
    .dash-card Digits {
        color: #f5f7fb;
        margin: 1 0;
    }
    .core-row {
        height: auto;
        margin-bottom: 1;
    }
    .core-label {
        width: 8;
        color: #8aa5c5;
    }
    .stats-row {
        height: auto;
        border: round #30415f;
        padding: 1 2;
        background: #111a2b;
        margin-bottom: 1;
    }
    ProgressBar {
        width: 100%;
        margin-bottom: 0;
    }
    ProgressBar > .bar--bar {
        color: #6ea8fe;
        background: #1a2539;
    }
    ProgressBar > .bar--complete {
        color: #8bd5ca;
    }
    Sparkline {
        width: 100%;
        height: 6;
        color: #f4b8e4;
    }
    #dash-net-spark {
        height: 3;
        color: #6ea8fe;
    }
    DataTable {
        height: 100%;
        background: #111a2b;
        color: #d9e4f5;
        border: round #30415f;
    }
    DataTable > .datatable--header {
        background: #1c2a42;
        color: #f5f7fb;
        text-style: bold;
    }
    DataTable > .datatable--cursor {
        background: #263754;
    }
    #log-sidebar {
        width: 25;
        border-right: solid #30415f;
        padding: 1;
    }
    #log-sources {
        background: #0f1728;
    }
    ListItem {
        padding: 0 1;
    }
    ListItem:hover {
        background: #18243a;
    }
    ListItem.--highlight {
        background: #263754;
        color: #f5f7fb;
    }
    #log-content-area {
        padding: 1;
    }
    #log-text {
        height: 100%;
        overflow-y: scroll;
        background: #111a2b;
        border: round #30415f;
        padding: 1;
    }
    .gpu-card {
        border: round #30415f;
        padding: 1 2;
        background: #111a2b;
        margin-bottom: 1;
        height: auto;
    }
    .gpu-card Sparkline {
        height: 3;
        margin: 1 0;
    }
    """

    def __init__(self, mock=False):
        super().__init__()
        self.monitor = Monitor(mock=mock)

    def action_next_tab(self) -> None:
        tc = self.query_one(TabbedContent)
        panes = list(tc.query(TabPane))
        if not panes:
            return
        current = next((i for i, pane in enumerate(panes) if pane.id == tc.active), 0)
        tc.active = panes[(current + 1) % len(panes)].id

    def action_previous_tab(self) -> None:
        tc = self.query_one(TabbedContent)
        panes = list(tc.query(TabPane))
        if not panes:
            return
        current = next((i for i, pane in enumerate(panes) if pane.id == tc.active), 0)
        tc.active = panes[(current - 1) % len(panes)].id

    def action_switch_tab(self, index: int) -> None:
        tc = self.query_one(TabbedContent)
        panes = list(tc.query(TabPane))
        if index < len(panes):
            tc.active = panes[index].id

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with TabbedContent(id="tabs-main"):
            with TabPane("Dash", id="tab-dash"):
                self.dash_widget = DashboardWidget()
                yield self.dash_widget
            with TabPane("CPU", id="tab-cpu"):
                self.cpu_widget = CPUWidget(self.monitor)
                yield self.cpu_widget
            with TabPane("Proc", id="tab-proc"):
                self.proc_widget = ProcessWidget()
                yield self.proc_widget
            with TabPane("Memory", id="tab-mem"):
                self.mem_widget = MemoryWidget()
                yield self.mem_widget
            with TabPane("SMART", id="tab-health"):
                self.health_widget = DiskHealthWidget()
                yield self.health_widget
            with TabPane("Logs", id="tab-logs"):
                yield LogViewerWidget(self.monitor)
            with TabPane("Net", id="tab-net"):
                self.net_widget = NetworkWidget()
                yield self.net_widget
            with TabPane("Disk", id="tab-disk"):
                self.disk_widget = DiskWidget()
                yield self.disk_widget
            with TabPane("Conn", id="tab-conn"):
                self.conn_widget = ConnectionsWidget()
                yield self.conn_widget
            with TabPane("GPU", id="tab-gpu"):
                self.gpu_widget = GPUWidget()
                yield self.gpu_widget
            with TabPane("About", id="tab-about"):
                yield AboutWidget()
        yield Footer()

    def on_mount(self) -> None:
        self.set_interval(1.0, self.refresh_stats)

    def refresh_stats(self) -> None:
        # Get all stats from monitor
        cpu_stats = self.monitor.get_cpu_stats()
        mem_stats = self.monitor.get_memory_stats()
        net_stats = self.monitor.get_network_stats()
        disk_stats = self.monitor.get_disk_stats()
        gpu_stats = self.monitor.get_gpu_stats()
        proc_stats = self.monitor.get_process_list()
        conn_stats = self.monitor.get_network_connections()
        health_stats = self.monitor.get_disk_health()
        sys_info = self.monitor.get_system_info()

        # Update Dashboard
        cpu_avg = sum(cpu_stats) / len(cpu_stats) if cpu_stats else 0
        self.dash_widget.update_stats(cpu_avg, mem_stats, net_stats, sys_info)

        # Update Individual Widgets
        self.cpu_widget.update_stats(cpu_stats)
        self.mem_widget.update_stats(*mem_stats)
        self.net_widget.update_stats(*net_stats)
        self.proc_widget.update_stats(proc_stats)
        self.disk_widget.update_stats(*disk_stats)
        self.conn_widget.update_stats(conn_stats)
        self.gpu_widget.update_stats(gpu_stats)
        self.health_widget.update_stats(health_stats)

if __name__ == "__main__":
    mock = "--mock" in sys.argv
    app = TaskManagerApp(mock=mock)
    app.run()
