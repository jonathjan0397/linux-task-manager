import sys
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, ProgressBar, Sparkline, Label, DataTable, TabbedContent, TabPane
from textual.containers import Container, Vertical, Horizontal
from monitor import Monitor

class CPUWidget(Static):
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("CPU Cores Usage")
            self.bars = []
            for i in range(16): # Support up to 16 cores
                bar = ProgressBar(total=100, show_percentage=True, id=f"cpu-{i}")
                bar.display = False
                self.bars.append(bar)
                yield bar

    def update_stats(self, stats):
        for i, val in enumerate(stats):
            if i < len(self.bars):
                self.bars[i].display = True
                self.bars[i].progress = val

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
        self.download_label.update(f"{down:.1f} KB/s")
        self.upload_label.update(f"{up:.1f} KB/s")

class ConnectionsWidget(Static):
    def compose(self) -> ComposeResult:
        yield Label("Active Network Connections")
        self.table = DataTable()
        self.table.add_columns("Local Address", "Remote Address", "Status", "PID")
        yield self.table

    def update_stats(self, connections):
        self.table.clear()
        for conn in connections:
            self.table.add_row(
                conn['laddr'],
                conn['raddr'],
                conn['status'],
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
        self.read_label.update(f"{read:.1f} KB/s")
        self.write_label.update(f"{write:.1f} KB/s")

class GPUWidget(Static):
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("GPU Performance")
            self.gpu_info = Static("Searching for GPUs...")
            yield self.gpu_info

    def update_stats(self, gpus):
        if not gpus:
            self.gpu_info.update("No compatible GPUs detected.")
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
            self.table.add_row(
                str(proc['pid']),
                proc['name'],
                f"{proc['cpu']}%",
                f"{proc['mem']:.1f}%"
            )

class TaskManagerApp(App):
    CSS = """
    Screen {
        background: #1a1b26;
    }
    TabPane {
        padding: 1 2;
    }
    Label {
        color: #7aa2f7;
        text-style: bold;
        margin-bottom: 1;
    }
    .stats-row {
        height: auto;
        border: solid #414868;
        padding: 1;
    }
    ProgressBar {
        width: 100%;
        margin-bottom: 0;
    }
    Sparkline {
        width: 100%;
        height: 10;
        color: #bb9af7;
    }
    DataTable {
        height: 100%;
        border: none;
    }
    """

    def __init__(self, mock=False):
        super().__init__()
        self.monitor = Monitor(mock=mock)

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent():
            with TabPane("CPU"):
                self.cpu_widget = CPUWidget()
                yield self.cpu_widget
            with TabPane("Network"):
                self.net_widget = NetworkWidget()
                yield self.net_widget
            with TabPane("Connections"):
                self.conn_widget = ConnectionsWidget()
                yield self.conn_widget
            with TabPane("Disk"):
                self.disk_widget = DiskWidget()
                yield self.disk_widget
            with TabPane("GPU"):
                self.gpu_widget = GPUWidget()
                yield self.gpu_widget
            with TabPane("Processes"):
                self.proc_widget = ProcessWidget()
                yield self.proc_widget
        yield Footer()

    def on_mount(self) -> None:
        self.set_interval(1.0, self.refresh_stats)

    def refresh_stats(self) -> None:
        # Only update the active tab's data for performance if needed, 
        # but for now we update all to keep sparklines flowing.
        cpu_stats = self.monitor.get_cpu_stats()
        self.cpu_widget.update_stats(cpu_stats)

        net_down, net_up = self.monitor.get_network_stats()
        self.net_widget.update_stats(net_down, net_up)

        conn_stats = self.monitor.get_network_connections()
        self.conn_widget.update_stats(conn_stats)

        disk_read, disk_write = self.monitor.get_disk_stats()
        self.disk_widget.update_stats(disk_read, disk_write)

        gpu_stats = self.monitor.get_gpu_stats()
        self.gpu_widget.update_stats(gpu_stats)

        proc_stats = self.monitor.get_process_list()
        self.proc_widget.update_stats(proc_stats)

if __name__ == "__main__":
    mock = "--mock" in sys.argv
    app = TaskManagerApp(mock=mock)
    app.run()
