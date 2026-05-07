"""
OPC UA知识图谱自动建模系统 - 单元测试
"""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from knowledge_graph.triple_store import Triple, TripleStore
from knowledge_graph.builder import KnowledgeGraphBuilder
from knowledge_graph.imkg.device_kgs import IMKG_BUILDERS

from model_generation.owl_to_nodeset import OWLToNodesetXML
from model_generation.format_agent import FormatTransformationAgent
from model_generation.address_space import AddressSpaceBuilder

from data.training_generator import TrainingDataGenerator
from data.sample_generator import SampleData

from eval.metrics import compute_ranking_metrics
from eval.evaluator import PipelineEvaluator

try:
    from device_identification.preprocessor import CharPreprocessor
    from device_identification.textcnn import (
        DEVICE_TYPE_LABELS,
        DEVICE_TYPE_NAMES,
        get_device_type_name,
        get_label_info,
    )
except ImportError:
    CharPreprocessor = None
    DEVICE_TYPE_LABELS = {}
    DEVICE_TYPE_NAMES = {}
    def get_device_type_name(label):
        return "Unknown"
    def get_label_info(idx):
        return {}


class TestDeviceIdentification(unittest.TestCase):
    """设备类型识别测试"""

    def setUp(self):
        self.preprocessor = CharPreprocessor(max_sequence_length=64)

    def test_preprocessor_build_vocab(self):
        texts = ["Spindle", "CNC", "RobotArm", "AxisCount", "FeedRate"]
        self.preprocessor.build_vocab(texts)
        self.assertGreater(self.preprocessor.vocab_size, 2)

    def test_preprocessor_encode(self):
        texts = ["Spindle", "CNC", "ToolChanger"]
        self.preprocessor.build_vocab(texts)
        encoded = self.preprocessor.encode("Spindle")
        self.assertEqual(len(encoded), 64)
        encoded2 = self.preprocessor.encode("CNC")
        self.assertEqual(len(encoded2), 64)

    def test_preprocessor_save_load(self):
        texts = ["Spindle", "RobotArm", "AxisCount"]
        self.preprocessor.build_vocab(texts)
        save_path = "data/training/device_classification/test_vocab.json"
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        self.preprocessor.save(save_path)

        loaded = CharPreprocessor.load(save_path)
        self.assertEqual(loaded.vocab_size, self.preprocessor.vocab_size)

    def test_device_type_labels(self):
        self.assertEqual(DEVICE_TYPE_LABELS[0], "IR")
        self.assertEqual(DEVICE_TYPE_LABELS[1], "CNC")
        self.assertEqual(DEVICE_TYPE_LABELS[5], "PW")
        self.assertEqual(len(DEVICE_TYPE_LABELS), 6)

    def test_get_device_name(self):
        self.assertEqual(get_device_type_name("IR"), "Industrial Robot")
        self.assertEqual(get_device_type_name("CNC"), "CNC Machine")
        self.assertEqual(get_device_type_name("ZZZ"), "Unknown")

    def test_label_info(self):
        info = get_label_info(0)
        self.assertEqual(info["label"], "IR")
        self.assertEqual(info["name"], "Industrial Robot")


class TestKnowledgeGraph(unittest.TestCase):
    """知识图谱测试"""

    def test_triple_store_add(self):
        store = TripleStore()
        t = Triple("A", "hasProperty", "B", "Object", "Variable")
        store.add_triple(t)
        self.assertEqual(store.triple_count, 1)
        self.assertEqual(store.entity_count, 2)

    def test_triple_store_query(self):
        store = TripleStore()
        store.add_triple(Triple("CNC", "hasComponent", "Spindle", "Object", "Object"))
        store.add_triple(Triple("Spindle", "hasProperty", "Speed", "Object", "Variable"))

        by_head = store.query_by_head("CNC")
        self.assertEqual(len(by_head), 1)

        by_tail = store.query_by_tail("Spindle")
        self.assertEqual(len(by_tail), 1)

        neighbors = store.get_neighbors("Spindle")
        self.assertEqual(len(neighbors), 2)

    def test_triple_store_dedup(self):
        store = TripleStore()
        t = Triple("A", "hasPart", "B")
        store.add_triple(t)
        store.add_triple(t)
        self.assertEqual(store.triple_count, 1)

    def test_triple_store_stats(self):
        store = TripleStore()
        store.add_triple(Triple("A", "r1", "B"))
        store.add_triple(Triple("B", "r2", "C"))
        stats = store.get_statistics()
        self.assertEqual(stats["triple_count"], 2)
        self.assertEqual(stats["entity_count"], 3)

    def test_imkg_builders(self):
        for device_type in ["IR", "CNC", "SOM", "SCM", "PM", "PW"]:
            builder = IMKG_BUILDERS.get(device_type)
            self.assertIsNotNone(builder, f"缺少{device_type}的IMKG构建器")
            triples = builder()
            self.assertIsInstance(triples, list)
            self.assertGreater(len(triples), 0, f"{device_type}的IMKG为空")

    def test_kg_builder(self):
        builder = KnowledgeGraphBuilder()
        store = builder.build_from_device_type("CNC")
        self.assertIsNotNone(store)
        self.assertGreater(store.triple_count, 5)
        self.assertGreater(store.entity_count, 3)

    def test_kg_builder_mappings(self):
        builder = KnowledgeGraphBuilder()
        builder.build_from_device_type("CNC")
        self.assertGreater(builder.num_entities, 0)
        self.assertGreater(builder.num_relations, 0)

    def test_triple_store_dict(self):
        store = TripleStore()
        store.add_triple(Triple("H", "R", "T"))
        d = store.to_dict()
        self.assertIn("triples", d)
        self.assertIn("entities", d)


class TestKnowledgeCompletion(unittest.TestCase):
    """知识补全测试"""

    def test_cbow_init(self):
        try:
            import torch
            from knowledge_completion.cbow import CBOW
            model = CBOW(vocab_size=50, embedding_dim=32, window_size=3)
            x = torch.randint(0, 50, (4, 6))
            out = model(x)
            self.assertEqual(out.shape, (4, 50))
        except ImportError:
            self.skipTest("PyTorch not available")

    def test_complex_init(self):
        try:
            import torch
            from knowledge_completion.complex_model import ComplEx
            model = ComplEx(num_entities=10, num_relations=5, embedding_dim=128)
            head = torch.tensor([0, 1, 2])
            rel = torch.tensor([0, 1, 0])
            tail = torch.tensor([3, 4, 5])
            scores = model(head, rel, tail)
            self.assertEqual(scores.shape, (3,))
        except ImportError:
            self.skipTest("PyTorch not available")

    def test_ranking_metrics(self):
        ranks = [1, 2, 1, 5, 3, 10, 2]
        metrics = compute_ranking_metrics(ranks)
        self.assertGreater(metrics["mrr"], 0)
        self.assertGreaterEqual(metrics["hit@1"], 0)
        self.assertGreaterEqual(metrics["hit@3"], 0)

    def test_ranking_perfect(self):
        ranks = [1] * 10
        metrics = compute_ranking_metrics(ranks)
        self.assertAlmostEqual(metrics["mrr"], 1.0)
        self.assertAlmostEqual(metrics["hit@1"], 1.0)
        self.assertAlmostEqual(metrics["hit@3"], 1.0)


class TestModelGeneration(unittest.TestCase):
    """模型生成测试"""

    def test_owl_converter(self):
        from model_generation.imkg_to_owl import IMKGToOWL
        from knowledge_graph.triple_store import Triple, TripleStore

        store = TripleStore()
        store.add_triple(Triple("Device", "hasComponent", "Part", "Object", "Object"))
        store.add_triple(Triple("Part", "hasProperty", "Value", "Object", "Variable"))

        converter = IMKGToOWL()
        owl = converter.convert(store, device_type="Test")
        self.assertIn("RDF", owl)
        self.assertIn("Device", owl)
        self.assertIn("Part", owl)

    def test_nodeset_converter(self):
        from knowledge_graph.triple_store import Triple, TripleStore

        store = TripleStore()
        store.add_triple(Triple("Device", "hasProperty", "Speed", "Object", "Variable"))
        store.add_triple(Triple("Device", "hasComponent", "Component", "Object", "Object"))

        converter = OWLToNodesetXML()
        xml = converter.convert_from_kg(store, device_type="Test")
        self.assertIn("UANodeSet", xml)
        self.assertIn("Device", xml)

    def test_format_agent_sa(self):
        fta = FormatTransformationAgent()
        sa = {
            "device_name": "TestDevice",
            "objects": [
                {
                    "name": "SubComponent",
                    "variables": [
                        {"name": "Temp", "value": "25", "data_type": "Double"}
                    ],
                }
            ],
        }
        result = fta.convert_from_sa(sa, device_type="TEST")
        self.assertIn("nodes", result)
        self.assertEqual(result["device_type"], "TEST")

    def test_format_agent_nodeset(self):
        fta = FormatTransformationAgent()
        sa = {"device_name": "TestDevice"}
        result = fta.convert_from_sa(sa, device_type="TEST")
        xml = fta.to_nodeset_xml(result)
        self.assertIn("UANodeSet", xml)

    def test_address_space_builder(self):
        builder = AddressSpaceBuilder()
        from knowledge_graph.triple_store import Triple, TripleStore

        store = TripleStore()
        store.add_triple(Triple("Root", "hasComponent", "Child", "Object", "Object"))
        store.add_triple(Triple("Child", "hasProperty", "Value", "Object", "Variable"))

        space = builder.build_from_kg(store, device_type="TEST")
        self.assertIsNotNone(space)


class TestTrainingData(unittest.TestCase):
    """训练数据生成测试"""

    def test_generator_create(self):
        gen = TrainingDataGenerator()
        self.assertIsNotNone(gen)

    def test_generate_classification(self):
        gen = TrainingDataGenerator()
        encoded, labels = gen.generate_classification_data(samples_per_class=50)
        self.assertGreater(len(encoded), 0)
        self.assertEqual(len(encoded), len(labels))
        self.assertTrue(Path("data/training/device_classification/char_vocab.json").exists())
        self.assertTrue(Path("data/training/device_classification/label_map.json").exists())

    def test_generate_cbow(self):
        gen = TrainingDataGenerator()
        data = gen.generate_cbow_data()
        self.assertIn("entity_names", data)
        self.assertIn("contexts", data)
        self.assertTrue(Path("data/training/cbow/vocab.json").exists())

    def test_generate_ner(self):
        gen = TrainingDataGenerator()
        data = gen.generate_ner_data()
        self.assertGreater(data["num_samples"], 0)

    def test_get_all_imkg_triples(self):
        gen = TrainingDataGenerator()
        triples = gen.get_all_imkg_triples()
        self.assertGreater(len(triples), 0)
        for t in triples[:3]:
            self.assertIn("head", t)
            self.assertIn("relation", t)
            self.assertIn("tail", t)


class TestSampleData(unittest.TestCase):
    """示例数据测试"""

    def test_create_frame(self):
        gen = SampleData()
        frame = gen.create_sample_frame()
        self.assertIn("nodes", frame)
        self.assertIn("device_metadata", frame)

    def test_create_sa(self):
        gen = SampleData()
        sa = gen.create_sample_sa()
        self.assertIn("device_name", sa)
        self.assertIn("objects", sa)

    def test_create_iea(self):
        gen = SampleData()
        iea = gen.create_sample_iea()
        self.assertIn("text", iea)
        self.assertIn("annotations", iea)


class TestEndToEnd(unittest.TestCase):
    """端到端测试"""

    def test_pipeline_evaluator(self):
        evaluator = PipelineEvaluator()
        samples = evaluator.generate_sample_data(20)
        self.assertEqual(len(samples), 20)

    def test_full_flow_without_ml(self):
        """不依赖ML框架的端到端流程测试"""
        sample_gen = SampleData()
        frame = sample_gen.create_sample_frame()

        self.assertIn("device_metadata", frame)
        self.assertGreater(len(frame["device_metadata"]), 0)

        for field in frame["device_metadata"][:5]:
            self.assertIn("field_name", field)
            self.assertIn("node_class", field)

        builder = KnowledgeGraphBuilder()
        store = builder.build_from_device_type("CNC")
        self.assertGreater(store.triple_count, 0)

        converter = OWLToNodesetXML()
        xml = converter.convert_from_kg(store, device_type="CNC")
        self.assertIn("UANodeSet", xml)

        fta = FormatTransformationAgent()
        sa = {
            "device_name": "CNC_Tester",
            "objects": [{"name": "Spindle"}],
        }
        result = fta.convert_from_sa(sa, device_type="CNC")
        nodeset = fta.to_nodeset_xml(result)
        self.assertIn("UANodeSet", nodeset)

        xml_path = "output/nodeset/test_e2e.xml"
        converter.save(xml, xml_path)
        self.assertTrue(Path(xml_path).exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
