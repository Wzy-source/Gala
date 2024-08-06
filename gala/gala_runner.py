from gala.graph import ICFGBuilder, ICFGSlicer, TaintAnalyzer
from gala.sequence import TxSequenceGenerator
from slither.core.declarations import Contract


class GalaRunner:
    def __init__(self):  # 组建注册
        self.icfg_builder: ICFGBuilder = ICFGBuilder()
        self.taint_analyzer: TaintAnalyzer = TaintAnalyzer()
        self.icfg_slicer: ICFGSlicer = ICFGSlicer()
        self.tx_sequence_generator: TxSequenceGenerator = TxSequenceGenerator()

    def run(self, main_contract: Contract):
        print("Gala Start Analysis")

        print("Step1: Build ICFG")
        icfg = self.icfg_builder.build(main_contract=main_contract)

        print("Step2: Slice Contract Functions")
        sliced_graph = self.icfg_slicer.slice(icfg=icfg)

        print("Step3: Taint Analysis")
        self.taint_analyzer.analyze(sliced_graph)

        print("Step4: Generate Tx Sequences")
        self.tx_sequence_generator.generate(sliced_graph)
