from gala.graph import ICFGBuilder, ICFGSlicer, TaintAnalyzer
from gala.sequence import TxSequenceGenerator
from slither.core.declarations import Contract
from slither.core.variables import Variable
from slither.slithir.operations import Operation
from typing import List, Dict, Callable
from gala.symbolic import SymbolicEngine


class GalaRunner:
    def __init__(self, main_contract: Contract):
        self.main_contract: Contract = main_contract
        # 组建注册
        self.icfg_builder: ICFGBuilder = ICFGBuilder()
        self.taint_analyzer: TaintAnalyzer = TaintAnalyzer()
        self.icfg_slicer: ICFGSlicer = ICFGSlicer()
        self.tx_sequence_generator: TxSequenceGenerator = TxSequenceGenerator()
        self.symbolic_engine: SymbolicEngine = SymbolicEngine()

    def run(self, program_points: List[Operation]) -> "GalaRunner":
        print("Gala Start Analysis")

        print("Step1: Build ICFG")
        icfg = self.icfg_builder.build(main_contract=self.main_contract)

        print("Step2: Slice Contract Functions")
        sliced_graph = self.icfg_slicer.slice(icfg=icfg)

        print("Step3: Taint Analysis")
        self.taint_analyzer.analyze(sliced_graph)

        print("Step4: Generate Tx Sequences")
        GeneratedTxSequences = self.tx_sequence_generator.generate(sliced_graph)

        print("Step5: Symbolic Execution")

        self.symbolic_engine.execute(sliced_graph, GeneratedTxSequences)

        return self

    def register_monitor_handlers(self, handlers: Dict[str, Callable]) -> "GalaRunner":
        for var_name, handler in handlers.items():
            var: Variable = self.main_contract.get_state_variable_from_name(var_name)
            if var is not None:
                self.symbolic_engine.variable_monitor.add_var_handler(var, handler)
        return self
