import unittest
import sys
import os
from typing import Dict

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core_pipeline.reasoning_engine import ReasoningEngine
from core_pipeline.coa_scorer import COAScorer
# Mocking dependencies for Agent test might be complex, so we'll focus on unit tests for components first

class TestCOAExtension(unittest.TestCase):
    
    def setUp(self):
        self.reasoning_engine = ReasoningEngine()
        self.coa_scorer = COAScorer()
        
    def test_reasoning_engine_methods(self):
        """Test that new methods in ReasoningEngine exist and return expected structure"""
        context = {"threat_level": 0.8}
        
        # Test Offensive
        result = self.reasoning_engine.run_offensive_rules(context)
        self.assertIn("COA", result)
        self.assertIn("Reason", result)
        print(f"Offensive Result: {result}")
        
        # Test Counter-attack
        result = self.reasoning_engine.run_counter_attack_rules(context)
        self.assertIn("COA", result)
        print(f"Counter-attack Result: {result}")
        
        # Test Generic Dispatcher
        result = self.reasoning_engine.run_coa_rules(context, "offensive")
        self.assertIn("COA", result)
        
        result = self.reasoning_engine.run_coa_rules(context, "maneuver")
        self.assertIn("COA", result)

    def test_coa_scorer_weights(self):
        """Test that COAScorer loads different weights for different types"""
        
        # Defense (Default)
        scorer_defense = COAScorer(coa_type="defense")
        weights_defense = scorer_defense.get_weights()
        print(f"Defense Weights: {weights_defense}")
        self.assertEqual(weights_defense.get('threat'), 0.25)
        
        # Offensive
        scorer_offensive = COAScorer(coa_type="offensive")
        weights_offensive = scorer_offensive.get_weights()
        print(f"Offensive Weights: {weights_offensive}")
        # Check if weights are different from default/defense
        # Note: In my implementation, offensive threat weight is 0.20
        self.assertEqual(weights_offensive.get('threat'), 0.20)
        self.assertEqual(weights_offensive.get('resources'), 0.25)
        
        # Deterrence
        scorer_deterrence = COAScorer(coa_type="deterrence")
        weights_deterrence = scorer_deterrence.get_weights()
        print(f"Deterrence Weights: {weights_deterrence}")
        self.assertEqual(weights_deterrence.get('assets'), 0.30)

if __name__ == '__main__':
    unittest.main()
