import sys
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, ProgressBar, Sparkline, Label, DataTable, TabbedContent, TabPane, Digits
from textual.containers import Container, Vertical, Horizontal, Grid
from monitor import Monitor

class DashboardWidget(Static):
    def compose(self) -> ComposeResult:
        with Vertical():
            with Horizontal(id="system-info-bar"):
                self.os_label = Label("OS: Loading...")
                self.uptime_label = Label("Uptime: Loading...")
                yield self.os_label
                yield self.uptime_label
            
            with Grid(id="dashboard-grid"):
                with Vertical(classes="dash-card"):
                    yield Label("Overall CPU")
                    self.cpu_digits = Digits("0%")
                    self.cpu_bar = ProgressBar(total=100, show_percentage=True)
                    yield self.cpu_digits
                    yield self.cpu_bar
                
                with Vertical(classes="dash-card"):
                    yield Label("Memory Usage")
                    self.mem_digits = Digits("0%")
                    self.mem_bar = ProgressBar(total=100, show_percentage=True)
                    self.mem_label = Label("0/0 GB")
                    yield self.mem_digits
                    yield self.mem_bar
                    yield self.mem_label

                with Vertical(classes="dash-card"):
                    yield Label("Network")
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

        # CPU
        self.cpu_digits.update(f"{cpu_avg:.0f}%")
        self.cpu_bar.progress = cpu_avg
        
        # Memory
        percent, used, total = mem_data
        self.mem_digits.update(f"{percent:.0f}%")
        self.mem_bar.progress = percent
        self.mem_label.update(f"{used:.1f} / {total:.1f} GB")

        # Network
        down, up = net_data
        self.net_down.update(f"Download: [cyan]{down:.1f} KB/s[/cyan]")
        self.net_up.update(f"Upload: [magenta]{up:.1f} KB/s[/magenta]")
        if self.net_spark.data is None:
            self.net_spark.data = []
        self.net_spark.data = self.net_spark.data + [down + up]

class CPUWidget(Static):
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Per-Core CPU Usage")
            self.bars = []
            for i in range(16): # Support up to 16 cores
                with Horizontal(classes="core-row"):
                    label = Label(f"Core {i:2d}", classes="core-label")
                    bar = ProgressBar(total=100, show_percentage=True, id=f"cpu-{i}")
                    bar.display = False
                    label.display = False
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
            yield Label("Detailed Memory Stats")
            self.main_bar = ProgressBar(total=100, show_percentage=True)
            self.stats_label = Label("Loading...")
            yield self.main_bar
            yield self.stats_label
            yield Label("\nMemory History")
            self.history = Sparkline()
            yield self.history

    def update_stats(self, percent, used, total):
        self.main_bar.progress = percent
        self.stats_label.update(f"Used: [bold]{used:.2f} GB[/bold] | Total: [bold]{total:.2f} GB[/bold]")
        if self.history.data is None:
            self.history.data = []
        self.history.data = self.history.data + [percent]

class NetworkWidget(Static):
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Network Traffic")
            with Horizontal(classes="stats-row"):
                with Vertical():
                    yield Label("Download Speed")
                    self.download_spark = Sparkline(id="net-down", summary_function=max)
                    self.download_label = Label("0 KB/s")
                    yield self.download_spark
                    yield self.download_label
                with Vertical():
                    yield Label("Upload Speed")
                    self.upload_spark = Sparkline(id="net-up", summary_function=max)
                    self.upload_label = Label("0 KB/s")
                    yield self.upload_spark
                    yield self.upload_label

    def update_stats(self, down, up):
        if self.download_spark.data is None:
            self.download_spark.data = []
        if self.upload_spark.data is None:
            self.upload_spark.data = []
        self.download_spark.data = self.download_spark.data + [down]
        self.upload_spark.data = self.upload_spark.data + [up]
        self.download_label.update(f"[cyan]{down:.1f} KB/s[/cyan]")
        self.upload_label.update(f"[magenta]{up:.1f} KB/s[/magenta]")

class ConnectionsWidget(Static):
    def compose(self) -> ComposeResult:
        yield Label("Active Network Connections")
        self.table = DataTable()
        self.table.add_columns("Local Address", "Remote Address", "Status", "PID")
        yield self.table

    def update_stats(self, connections):
        self.table.clear()
        for conn in connections:
            status = conn['status']
            if status == 'ESTABLISHED':
                status_display = f"[green]{status}[/]"
            elif status == 'LISTEN':
                status_display = f"[yellow]{status}[/]"
            else:
                status_display = status
            
            self.table.add_row(
                conn['laddr'],
                conn['raddr'],
                status_display,
                str(conn['pid'])
            )

class DiskWidget(Static):
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Disk I/O Activity")
            with Horizontal(classes="stats-row"):
                with Vertical():
                    yield Label("Read Throughput")
                    self.read_spark = Sparkline(id="disk-read", summary_function=max)
                    self.read_label = Label("0 KB/s")
                    yield self.read_spark
                    yield self.read_label
                with Vertical():
                    yield Label("Write Throughput")
                    self.write_spark = Sparkline(id="disk-write", summary_function=max)
                    self.write_label = Label("0 KB/s")
                    yield self.write_spark
                    yield self.write_label

    def update_stats(self, read, write):
        if self.read_spark.data is None:
            self.read_spark.data = []
        if self.write_spark.data is None:
            self.write_spark.data = []
        self.read_spark.data = self.read_spark.data + [read]
        self.write_spark.data = self.write_spark.data + [write]
        self.read_label.update(f"[blue]{read:.1f} KB/s[/blue]")
        self.write_label.update(f"[orange3]{write:.1f} KB/s[/orange3]")

class DiskHealthWidget(Static):
    def compose(self) -> ComposeResult:
        yield Label("Disk S.M.A.R.T. Health Assessment")
        self.table = DataTable()
        self.table.add_columns(" ", "Device", "Model", "Status", "Temp", "Power On", "Reallocated")
        yield self.table

    def update_stats(self, disks):
        self.table.clear()
        if not disks:
            self.table.add_row("", "No disks detected or insufficient permissions (need sudo)", "-", "-", "-", "-", "-")
            return

        for disk in disks:
            status_style = "[green]" if disk['status'] == "PASSED" else "[bold red]"
            icon = "✅" if disk['status'] == "PASSED" else "⚠️"
            if disk.get('alert'):
                status_style = "[bold red]"
                icon = "🚨"

            self.table.add_row(
                icon,
                disk['device'],
                disk['model'],
                f"{status_style}{disk['status']}[/]",
                disk['temp'],
                disk['power_on'],
                f"[bold red]{disk['reallocated']}[/]" if disk['reallocated'] > 0 else str(disk['reallocated'])
            )

class GPUWidget(Static):
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("GPU Performance")
            self.gpu_info = Static("Searching for GPUs...")
            yield self.gpu_info

    def update_stats(self, gpus):
        if not gpus:
            self.gpu_info.update("[dim]No compatible GPUs detected.[/dim]")
            return
        
        info = ""
        for gpu in gpus:
            info += f"[bold cyan]{gpu.get('name', 'Unknown GPU')}[/bold cyan]\n"
            info += f"Utilization: [green]{gpu['util']}%[/green]\n"
            info += f"Memory: [yellow]{gpu['mem']:.1f}%[/yellow]\n\n"
        self.gpu_info.update(info)

class ProcessWidget(Static):
    def compose(self) -> ComposeResult:
        yield Label("Top System Processes")
        self.table = DataTable()
        self.table.add_columns("PID", "Name", "CPU%", "MEM%")
        yield self.table

    def update_stats(self, processes):
        self.table.clear()
        for proc in processes:
            cpu = proc['cpu']
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

class AboutWidget(Static):
    def compose(self) -> ComposeResult:
        yield Label("About PyTask: Linux Task Manager")
        yield Static(
            "\n[bold cyan]PyTask[/bold cyan] is a modern, terminal-based system monitor.\n\n"
            "Built with [bold]Python[/bold] and the [bold]Textual[/bold] framework.\n\n"
            "Features:\n"
            " - Real-time CPU & Memory monitoring\n"
            " - Network traffic & active connections\n"
            " - Disk I/O & S.M.A.R.T. health data\n"
            " - GPU performance tracking\n"
            " - Process management\n\n"
            "Created for the [bold green]Linux[/bold green] community.\n"
            "Version: [bold yellow]1.1.0[/bold yellow]\n\n"
            "Shortcut Keys:\n"
            " [bold yellow]1-9[/bold yellow]: Switch Tabs\n"
            " [bold yellow]t / T[/bold yellow]: Next / Previous Tab\n"
            " [bold yellow]Esc / q[/bold yellow]: Exit App"
        )

class TaskManagerApp(App):
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("escape", "quit", "Exit"),
        ("t", "next_tab", "Next Tab"),
        ("shift+t", "previous_tab", "Prev Tab"),
        ("1", "switch_tab(0)", "Dashboard"),
        ("2", "switch_tab(1)", "CPU"),
        ("3", "switch_tab(2)", "Processes"),
        ("4", "switch_tab(3)", "Memory"),
        ("5", "switch_tab(4)", "Health"),
        ("6", "switch_tab(5)", "Network"),
        ("7", "switch_tab(6)", "Disk"),
        ("8", "switch_tab(7)", "Connections"),
        ("9", "switch_tab(9)", "About"),
    ]
    CSS = """
    Screen {
        background: black;
        color: #00FF00;
    }
    Header {
        background: black;
        color: #00FF00;
        border-bottom: solid white;
    }
    Footer {
        background: black;
        color: #00FF00;
        border-top: solid white;
        height: 1;
        dock: bottom;
    }
    Footer > .footer--key {
        color: #00FF00;
        background: black;
    }
    Footer > .footer--description {
        color: #00FF00;
    }
    Footer > .footer--highlight {
        background: #004400;
    }
    #system-info-bar {
        height: 3;
        border-bottom: solid white;
        padding: 0 1;
        background: #001100;
        align: center middle;
    }
    #system-info-bar Label {
        margin: 0 4;
    }
    TabbedContent {
        background: black;
        height: 100%;
    }
    Tabs {
        background: black;
        border-bottom: solid white;
    }
    Tab {
        color: #00FF00;
    }
    Tab:focus {
        background: #004400;
    }
    TabPane {
        padding: 1 2;
        background: black;
        border: solid white;
        margin: 1;
        height: 100%;
    }
    Label {
        color: #00FF00;
        text-style: bold;
        margin-bottom: 1;
    }
    Static {
        color: #00FF00;
    }
    #dashboard-grid {
        grid-size: 3 1;
        grid-gutter: 2;
        height: 15;
    }
    .dash-card {
        border: solid white;
        padding: 1;
        background: black;
        align: center middle;
        text-align: center;
    }
    .dash-card Digits {
        color: #00FF00;
        margin: 1 0;
    }
    .core-row {
        height: auto;
        margin-bottom: 0;
    }
    .core-label {
        width: 8;
        color: #00FF00;
    }
    .stats-row {
        height: auto;
        border: solid white;
        padding: 1;
        margin-bottom: 1;
    }
    ProgressBar {
        width: 100%;
        margin-bottom: 0;
    }
    ProgressBar > .bar--bar {
        color: #00FF00;
        background: #002200;
    }
    ProgressBar > .bar--complete {
        color: #00FF00;
    }
    Sparkline {
        width: 100%;
        height: 6;
        color: #00FF00;
    }
    #dash-net-spark {
        height: 3;
        color: #00FF00;
    }
    DataTable {
        height: 100%;
        background: black;
        color: #00FF00;
        border: none;
    }
    DataTable > .datatable--header {
        background: #002200;
        color: #00FF00;
        text-style: bold;
    }
    DataTable > .datatable--cursor {
        background: #004400;
    }
    """

    def __init__(self, mock=False):
        super().__init__()
        self.monitor = Monitor(mock=mock)

    def action_next_tab(self) -> None:
        tc = self.query_one(TabbedContent)
        tc.active = tc.active_tab

    def action_switch_tab(self, index: int) -> None:
        tc = self.query_one(TabbedContent)
        # Use child panes to determine tab order
        panes = list(tc.query(TabPane))
        if index < len(panes):
            tc.active = panes[index].id

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with TabbedContent():
            with TabPane("Dashboard", id="tab-dash"):
                self.dash_widget = DashboardWidget()
                yield self.dash_widget
            with TabPane("CPU", id="tab-cpu"):
                self.cpu_widget = CPUWidget()
                yield self.cpu_widget
            with TabPane("Processes", id="tab-proc"):
                self.proc_widget = ProcessWidget()
                yield self.proc_widget
            with TabPane("Memory", id="tab-mem"):
                self.mem_widget = MemoryWidget()
                yield self.mem_widget
            with TabPane("Health", id="tab-health"):
                self.health_widget = DiskHealthWidget()
                yield self.health_widget
            with TabPane("Network", id="tab-net"):
                self.net_widget = NetworkWidget()
                yield self.net_widget
            with TabPane("Disk", id="tab-disk"):
                self.disk_widget = DiskWidget()
                yield self.disk_widget
            with TabPane("Connections", id="tab-conn"):
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
