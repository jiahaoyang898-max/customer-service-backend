from typing import List

from domain.contexts import TaskContext, StartedSystemContext, InterruptedSystemContext, ResumedSystemContext, \
    CanceledSystemContext
from domain.state import DialogueState
from task.command.models import Command, StartFlowCommand, SetSlotsCommand, CancelFlowCommand, ResumeFlowCommand
from task.flow.flows import FlowsList

class CommandProcessor:
    def run(
            self,
            commands: List[Command],
            state: DialogueState,
            flows:FlowsList,
    )->None:
        """
        把命令应用到state
        """
        for command in commands:
            self._apply(command, state, flows)

    def _apply(self, command: Command, state: DialogueState, flows: FlowsList)->None:
        """
        处理命令
        """
        if isinstance(command, StartFlowCommand):
            self._handle_start_flow(command, state, flows)
        elif isinstance(command, SetSlotsCommand):
            self._handle_set_slots(command, state)
        elif isinstance(command, CancelFlowCommand):
            self._handle_cancel_flow(state, flows)
        elif isinstance(command, ResumeFlowCommand):
            self._handle_resume_flow(command, state, flows)

    #一、开启流程
    def _handle_start_flow(self, command: StartFlowCommand, state: DialogueState, flows: FlowsList) -> None:
        """
        开启业务任务
        """
        #清理当前系统流程
        state.end_active_system_task()
        #防御：不允许直接启动system_开头的内部流程
        if command.flow.startswith("system_"):
            raise ValueError(f"不能直接启动系统流程：‘{command.flow}")
        #校验：流程必须存在
        target_flow = flows.get_flow_by_id(command.flow)
        if target_flow is None:
            raise ValueError(f"未知流程：'{command.flow}'")
        #校验:流程必须有起点
        start_step = target_flow.start_step()
        if start_step is None:
            raise ValueError(f"流程'{command.flow}'没有开始步骤")
        active_task = state.active_task
        #情况一：当前有活跃任务
        if active_task is not None:
            #同一个流程：不重复启动
            if active_task.flow_id == command.flow:
                return
            #不是同一个流程：把当前任务放进暂停栈
            interrupted_flow_id = active_task.flow_id
            interrupted_flow_name = self._readable_flow_name(active_task.flow_id,flows)
            state.interrupted_active_task()
            #试着从暂停栈恢复要开的流程
            resumed = state.resumed_active_task(command.flow)
            if not resumed:
                #要开的流程不在 暂停栈 新建
                state.start_active_task(TaskContext(flow_id=command.flow,step_id=start_step.id))
                started_flow_id = command.flow
                started_flow_name = self._readable_flow_name(command.flow,flows)
            else:
                # 要开的流程在暂停栈 → 已被 resumed_active_task 恢复
                started_flow_id = command.flow
                started_flow_name = self._readable_flow_name(command.flow, flows)
            # 激活"打断"过场
            self._activate_interrupted_system_flow(
                state, flows, interrupted_flow_id, interrupted_flow_name,
                started_flow_id, started_flow_name
            )
            return
        #情况二：当前没有活跃任务
        #试着恢复同名任务
        resumed = state.resumed_active_task(command.flow)
        if resumed:
            #要开的流程在暂停栈 恢复
            self._activate_resumed_system_flow(state, flows,command.flow, self._readable_flow_name(command.flow, flows))
            return
        # 要开的流程从没做过 新建
        state.start_active_task(TaskContext(flow_id=command.flow, step_id=start_step.id))
        self._activate_started_system_flow(state, flows, command.flow, self._readable_flow_name(command.flow, flows),)

    @staticmethod
    def _readable_flow_name(flow_id: str, flows: FlowsList) -> str:
        #取流程显示名
        flow = flows.get_flow_by_id(flow_id)
        return flow.name if flow else flow_id

    #三个激活系统的过场
    @staticmethod
    def _activate_started_system_flow(state: DialogueState, flows: FlowsList, started_flow_id: str, started_flow_name: str):
        """
        激活已启动的系统流程
        """
        flow = flows.get_flow_by_id("system_task_started")
        state.start_active_system_task(StartedSystemContext(
            flow_id="system_task_started",
            step_id=flow.start_step().id,
            started_flow_id=started_flow_id,
            started_flow_name=started_flow_name,
        ))

    @staticmethod
    def _activate_interrupted_system_flow(
            state: DialogueState, flows: FlowsList, interrupted_flow_id: str, interrupted_flow_name: str,
            started_flow_id: str, started_flow_name: str):

        flow = flows.get_flow_by_id("system_task_interrupted")
        state.start_active_system_task(InterruptedSystemContext(
            flow_id=flow.id,
            step_id=flow.start_step().id,
            interrupted_flow_id=interrupted_flow_id,
            interrupted_flow_name=interrupted_flow_name,
            started_flow_id=started_flow_id,
            started_flow_name=started_flow_name
        ))

    @staticmethod
    def _activate_resumed_system_flow(
            state: DialogueState, flows: FlowsList,
            resumed_flow_id: str, resumed_flow_name: str
    ):
        flow = flows.get_flow_by_id("system_task_resumed")
        state.start_active_system_task(ResumedSystemContext(
            flow_id=flow.id,
            step_id=flow.start_step().id,
            resumed_flow_id=resumed_flow_id,
            resumed_flow_name=resumed_flow_name
        ))

    #二、填写槽位
    def _handle_set_slots(self,command: SetSlotsCommand, state: DialogueState):
        if state.active_task:
            state.set_slots(command.slots)

    #三、取消流程(比如：取消退款)
    def _handle_cancel_flow(self,state:DialogueState,flows:FlowsList):
        #获取当前正在执行的flow
        active_task = state.active_task
        target_flow = flows.get_flow_by_id(active_task.flow_id)
        #取消当前task
        state.cancel_active_task()
        #启动 system_task_canceled（系统任务已取消） 过场
        state.start_active_system_task(
            CanceledSystemContext(
                flow_id="system_task_canceled",
                step_id=flows.get_flow_by_id("system_task_canceled").start_step().id,
                canceled_flow_id=target_flow.id,
                canceled_flow_name=target_flow.name,
            )
        )

    #四、恢复挂起的流程
    def _handle_resume_flow(self, command: ResumeFlowCommand, state: DialogueState, flows: FlowsList):
        #1.确定要恢复哪个流程
        if command.flow is not None:
            #明确恢复哪个流程
            target_flow = flows.get_flow_by_id(command.flow)
            if target_flow is None:
                raise ValueError(f"未知流程‘{command.flow}'.")
            target_flow_id = target_flow.id
            target_flow_name = target_flow.name
        else:
            #没有明确要恢复的流程（继续刚才的）
            if not state.paused_tasks:
                return
            top_paused = state.paused_tasks[-1]
            target_flow_id = top_paused.flow_id
            target_flow_name = self._readable_flow_name(target_flow_id,flows)
        #2.按当前有没有活跃任务恢复
        active_task = state.active_task
        if active_task is not None:
            if active_task.flow_id == target_flow_id:
                return
            interrupted_flow_id = active_task.flow_id
            interrupted_flow_name = self._readable_flow_name(active_task.flow_id,flows)
            state.interrupted_active_task()
            if not state.resumed_active_task(target_flow_id):
                #恢复失败 回退
                state.active_task = state.paused_tasks.pop()
                return
            self._activate_interrupted_system_flow(state, flows, interrupted_flow_id, interrupted_flow_name,
            target_flow_id, target_flow_name)
        else:
            if not state.resumed_active_task(target_flow_id):
                return
            resumed = state.active_task
            self._activate_resumed_system_flow(state, flows, resumed.flow_id, self._readable_flow_name(resumed.flow_id, flows))

if __name__ == '__main__':
    import sys
    from pathlib import Path

    # processor.py 在 task/command/ 下, parents[2] 是项目根
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

    from task.flow.loader import FlowLoader
    from domain.state import DialogueState
    from task.command.models import StartFlowCommand

    base = Path(__file__).resolve().parents[2]
    flows = FlowLoader().load_many([
        base / "flow_config" / "user_flows.yml",
        base / "flow_config" / "system_flows.yml",
    ])
    processor = CommandProcessor()

    # ================= 通用小工具 =================
    results = []

    def check(name, cond):
        results.append(cond)
        print(("  ✅ " if cond else "  ❌ ") + name)

    def new_state():
        return DialogueState(sender_id="u_test")

    def snap(s):
        task, sysf = s.active_task, s.active_system_task
        print(f"    active={task.flow_id if task else None}"
              f"  paused={[t.flow_id for t in s.paused_tasks]}"
              f"  过场={sysf.flow_id if sysf else None}")

    def start(s, flow, title):
        """模拟用户一句话发起流程, 并打印状态变化"""
        print(f"\n▶ {title}")
        processor.run([StartFlowCommand(command="start_flow", flow=flow)], s, flows)
        snap(s)

    # ================= 第4章: 每个用例一个函数 =================

    def test_4_1a_defense_system():
        """[4.1a] 防御: 启动 system_ 开头流程 → ValueError
        模拟场景: LLM 被诱导产出 system_task_started, 想直接启动内部流程"""
        s = new_state()
        try:
            processor.run([StartFlowCommand(command="start_flow", flow="system_task_started")], s, flows)
            check("[4.1a] 应抛 ValueError", False)
        except ValueError:
            check("[4.1a] system_ 开头 → ValueError", True)

    def test_4_1b_defense_unknown():
        """[4.1b] 防御: 流程不存在 → ValueError
        模拟场景: LLM 产出了配置里不存在的流程名"""
        s = new_state()
        try:
            processor.run([StartFlowCommand(command="start_flow", flow="no_such_flow")], s, flows)
            check("[4.1b] 应抛 ValueError", False)
        except ValueError:
            check("[4.1b] 未知流程 → ValueError", True)

    def test_4_1c_same_flow():
        """[4.1c] 有活跃任务 + 同流程 → 不重复启动
        模拟场景: 用户办着订单查询, 又说"再帮我查下订单状态" """
        s = new_state()
        start(s, "order_status_query", "用户: 我要查订单状态")
        start(s, "order_status_query", "用户: 再帮我查下订单状态")
        check("[4.1c] 同流程不重复", s.active_task.flow_id == "order_status_query")
        check("[4.1c] 暂停栈仍空", len(s.paused_tasks) == 0)

    def test_4_1d_interrupt_new():
        """[4.1d] 有活跃任务 + 不同流程 + 不在暂停栈 → 打断+新建 + Interrupted
        模拟场景: 用户查订单查到一半, 说"先帮我查物流" """
        s = new_state()
        start(s, "order_status_query", "用户: 我要查订单状态")
        start(s, "logistics_tracking", "用户: 先帮我查物流")
        check("[4.1d] active=物流查询", s.active_task.flow_id == "logistics_tracking")
        check("[4.1d] 订单状态进暂停栈", s.paused_tasks[0].flow_id == "order_status_query")
        check("[4.1d] Interrupted 过场", s.active_system_task.flow_id == "system_task_interrupted")

    def test_4_1e_interrupt_resume():
        """[4.1e] 有活跃任务 + 不同流程 + 在暂停栈 → 打断+恢复 + Interrupted
        模拟场景: 用户办着物流, 想起订单状态挂起过, 说"还是先看订单状态" """
        s = new_state()
        start(s, "order_status_query", "用户: 我要查订单状态")
        start(s, "logistics_tracking", "用户: 先帮我查物流")
        start(s, "order_status_query", "用户: 还是先看订单状态")
        check("[4.1e] active=订单状态", s.active_task.flow_id == "order_status_query")
        check("[4.1e] 物流进暂停栈", s.paused_tasks[-1].flow_id == "logistics_tracking")

    def test_4_2_resume():
        """[4.2] 无活跃任务 + 在暂停栈 → 恢复 + Resumed
        模拟场景: 退款之前被打断, 用户说"我要退款" → 从断点恢复, 不是重开"""
        s = new_state()
        start(s, "refund_request", "用户: 我要退款")
        s.interrupted_active_task()  # 手动模拟"退款被打断"挂起
        start(s, "refund_request", "用户: 我要退款(稍后)")
        check("[4.2] active=退款申请", s.active_task.flow_id == "refund_request")
        check("[4.2] 暂停栈清空", len(s.paused_tasks) == 0)
        check("[4.2] Resumed 过场", s.active_system_task.flow_id == "system_task_resumed")

    def test_4_3_new():
        """[4.3] 无活跃任务 + 不在暂停栈 → 新建 + Started
        模拟场景: 第一次查订单, 从没办过"""
        s = new_state()
        start(s, "order_status_query", "用户: 我要查订单状态")
        check("[4.3] active=订单状态", s.active_task.flow_id == "order_status_query")
        check("[4.3] step=start", s.active_task.step_id == "start")
        check("[4.3] Started 过场", s.active_system_task.flow_id == "system_task_started")

    # ================= 测试调度: 测哪个用例, 取消注释哪行 =================
    test_4_1a_defense_system()
    test_4_1b_defense_unknown()
    test_4_1c_same_flow()
    test_4_1d_interrupt_new()
    test_4_1e_interrupt_resume()
    test_4_2_resume()
    test_4_3_new()

    print(f"\n结果: {sum(results)}/{len(results)} 通过")

    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

    from task.flow.loader import FlowLoader
    from domain.state import DialogueState
    from domain.contexts import TaskContext
    from task.command.models import ResumeFlowCommand

    base = Path(__file__).resolve().parents[2]
    flows = FlowLoader().load_many([
        base / "flow_config" / "user_flows.yml",
        base / "flow_config" / "system_flows.yml",
    ])
    processor = CommandProcessor()

    # ================= 通用小工具 =================
    results = []


    def check(name, cond):
        results.append(cond)
        print(("  ✅ " if cond else "  ❌ ") + name)


    def new_state(active=None, paused=()):
        """手工摆好前置状态: new_state(active='物流', paused=['订单'])"""
        s = DialogueState(sender_id="u_test")
        if active:
            s.active_task = TaskContext(flow_id=active)
        s.paused_tasks = [TaskContext(flow_id=f) for f in paused]
        return s


    def resume(s, flow=None):
        """模拟用户说'继续刚才的(退款)', 并打印状态"""
        print(f"\n▶ resume(flow={flow})")
        processor.run([ResumeFlowCommand(command="resume_flow", flow=flow)], s, flows)
        task, sysf = s.active_task, s.active_system_task
        print(f"    active={task.flow_id if task else None}"
              f"  paused={[t.flow_id for t in s.paused_tasks]}"
              f"  过场={sysf.flow_id if sysf else None}")


    # ================= 第7章: 挂起恢复 4 种情况 =================

    def test_7_1_same_as_active():
        """[①] 要恢复的就是当前正办的 → 不重复, 无过场
        场景: 正查物流, 说"继续物流" —— 什么都不该变"""
        s = new_state(active="logistics_tracking", paused=["order_status_query"])
        resume(s, "logistics_tracking")
        check("[7-①] active 仍是物流", s.active_task.flow_id == "logistics_tracking")
        check("[7-①] 暂停栈不变", [t.flow_id for t in s.paused_tasks] == ["order_status_query"])
        check("[7-①] 无过场", s.active_system_task is None)


    def test_7_2_not_in_paused():
        """[②] 要恢复的不在暂停栈 → 回退, 静默无过场
        场景: 正查物流, 说"继续退款"(退款从没挂起过) —— 像没发生一样"""
        s = new_state(active="logistics_tracking", paused=["order_status_query"])
        resume(s, "refund_request")
        check("[7-②] 物流回退为 active", s.active_task.flow_id == "logistics_tracking")
        check("[7-②] 暂停栈只剩订单", [t.flow_id for t in s.paused_tasks] == ["order_status_query"])
        check("[7-②] 无过场", s.active_system_task is None)


    def test_7_3_interrupt_then_resume():
        """[③] 办 A 时回到挂起的 B → 打断 A + 恢复 B + Interrupted 过场
        场景: 正查物流, 说"继续刚才的退款" """
        s = new_state(active="logistics_tracking", paused=["refund_request"])
        resume(s, "refund_request")
        check("[7-③] active=退款", s.active_task.flow_id == "refund_request")
        check("[7-③] 物流反进暂停栈", [t.flow_id for t in s.paused_tasks] == ["logistics_tracking"])
        check("[7-③] Interrupted 过场", s.active_system_task.flow_id == "system_task_interrupted")


    def test_7_4_no_active():
        """[④] 没事做 → 直接恢复, 不指名取栈顶 + Resumed 过场
        场景: 订单、物流先后挂起, 说"继续刚才的" → 恢复最近的物流"""
        s = new_state(paused=["order_status_query", "logistics_tracking"])
        resume(s, None)  # flow=None: 用户只说"继续刚才的"
        check("[7-④] 恢复栈顶=物流", s.active_task.flow_id == "logistics_tracking")
        check("[7-④] 暂停栈剩订单", [t.flow_id for t in s.paused_tasks] == ["order_status_query"])
        check("[7-④] Resumed 过场", s.active_system_task.flow_id == "system_task_resumed")


    # ============ 测试调度: 测哪个用例, 注释掉其他行 ============
    test_7_1_same_as_active()
    test_7_2_not_in_paused()
    test_7_3_interrupt_then_resume()
    test_7_4_no_active()

    print(f"\n结果: {sum(results)}/{len(results)} 通过")







