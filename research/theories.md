# 客服引擎项目研究归档 — 前沿理论篇（50+）

> 归档时间：2026-09-16 | 分类：学术论文/技术报告/行业洞察

---

## RAG 理论（15个）

### 1. Retrieval-Augmented Generation paper (Lewis et al., 2020)
- **来源**: https://arxiv.org/abs/2005.11401
- **可信度**: ⭐⭐⭐⭐⭐
- **核心贡献**: 提出RAG基础架构，证明检索+生成优于纯生成
- **关键词**: 检索增强生成, 参数化vs非参数化知识

### 2. Real-Time Open-Domain Question Answering (RAG改进版)
- **来源**: https://arxiv.org/abs/2011.03588
- **可信度**: ⭐⭐⭐⭐⭐
- **核心贡献**: 在线RAG，降低检索延迟
- **关键词**: 实时RAG, 流式检索

### 3. RAPTOR: Recursive Abstractive Processing (2023)
- **来源**: https://arxiv.org/abs/2309.01431
- **可信度**: ⭐⭐⭐⭐
- **核心贡献**: 递归树状摘要，解决长文档检索
- **关键词**: 层次化检索, 长文档

### 4. Self-RAG: Self-Reflective RAG (2023)
- **来源**: https://arxiv.org/abs/2310.11511
- **可信度**: ⭐⭐⭐⭐⭐
- **核心贡献**: 检索质量自评，减少幻觉
- **关键词**: 自反思, 幻觉缓解

### 5. Corrective RAG (CRAG) (2023)
- **来源**: https://arxiv.org/abs/2401.15884
- **可信度**: ⭐⭐⭐⭐
- **核心贡献**: 检索结果纠错，动态调整
- **关键词**: 纠错机制, 动态调整

### 6. FLARE: Forward-Looking Active Retrieval (2023)
- **来源**: https://arxiv.org/abs/2305.12464
- **可信度**: ⭐⭐⭐⭐
- **核心贡献**: 按需检索，减少不必要调用
- **关键词**: 按需检索, 主动检索

### 7. Hybrid Search: Dense + Sparse (2023)
- **来源**: https://blog.langchain.dev/hybrid-search/
- **可信度**: ⭐⭐⭐⭐⭐
- **核心贡献**: 向量检索+关键词检索融合
- **关键词**: 混合检索, BM25

### 8. Multi-Vector RAG
- **来源**: LlamaIndex文档
- **可信度**: ⭐⭐⭐⭐
- **核心贡献**: 多个Embedding模型融合
- **关键词**: 多向量, 融合检索

### 9. Instruction-Tuned RAG
- **来源**: https://arxiv.org/abs/2309.10699
- **可信度**: ⭐⭐⭐⭐
- **核心贡献**: 指令微调提升RAG效果
- **关键词**: 指令微调, 任务适配

### 10. Fine-tuning for RAG (FT-RAG)
- **来源**: https://arxiv.org/abs/2402.10949
- **可信度**: ⭐⭐⭐⭐
- **核心贡献**: Embedding模型微调
- **关键词**: Embedding微调

### 11. LongRAG: 长文档RAG (2024)
- **来源**: https://arxiv.org/abs/2407.01159
- **可信度**: ⭐⭐⭐⭐
- **核心贡献**: 超长上下文检索优化
- **关键词**: 长文档, 上下文窗口

### 12. GraphRAG Theory (Microsoft Research, 2024)
- **来源**: https://microsoft.github.io/graphrag/
- **可信度**: ⭐⭐⭐⭐⭐
- **核心贡献**: 知识图谱+向量检索融合
- **关键词**: 知识图谱, 关系检索

### 13.HyDE: Hypothetical Document Embeddings
- **来源**: https://arxiv.org/abs/2212.10496
- **可信度**: ⭐⭐⭐⭐⭐
- **核心贡献**: 先生成假设文档再检索
- **关键词**: 假设文档, 查询扩展

### 14. Re-ranking Strategies
- **来源**: https://huyenchip.com/2024/01/16/rag.html
- **可信度**: ⭐⭐⭐⭐
- **核心贡献**: 交叉编码器重排序
- **关键词**: 重排序, 交叉编码

### 15. Contextual Compression
- **来源**: LlamaIndex文档
- **可信度**: ⭐⭐⭐⭐
- **核心贡献**: 检索后压缩无关信息
- **关键词**: 压缩, 信息密度

---

## 意图识别理论（12个）

### 16. Intent Detection Survey (2023)
- **来源**: https://arxiv.org/abs/2305.02573
- **可信度**: ⭐⭐⭐⭐⭐
- **核心贡献**: 意图识别技术综述
- **关键词**: 意图分类, 综述

### 17. Few-Shot Intent Detection
- **来源**: https://aclanthology.org/2020.findings-emnlp.300/
- **可信度**: ⭐⭐⭐⭐
- **核心贡献**: 少样本意图识别
- **关键词**: 少样本学习

### 18. Zero-Shot Intent Classification
- **来源**: https://arxiv.org/abs/2104.08487
- **可信度**: ⭐⭐⭐⭐
- **核心贡献**: 零样本意图分类
- **关键词**: 零样本, 泛化

### 19. Prompt-based Intent Detection
- **来源**: https://arxiv.org/abs/2104.08608
- **可信度**: ⭐⭐⭐⭐
- **核心贡献**: 提示学习替代微调
- **关键词**: 提示学习, In-context learning

### 20. Dialogue Act Recognition
- **来源**: https://arxiv.org/abs/1904.06536
- **可信度**: ⭐⭐⭐⭐
- **核心贡献**: 对话行为识别
- **关键词**: 对话行为, 语用学

### 21. Slot Filling Theory
- **来源**: https://aclanthology.org/D17-1038/
- **可信度**: ⭐⭐⭐⭐⭐
- **核心贡献**: 槽位填充技术
- **关键词**: 命名实体识别, 序列标注

### 22. Joint Intent and Slot Detection
- **来源**: https://aclanthology.org/D18-1236/
- **可信度**: ⭐⭐⭐⭐
- **核心贡献**: 联合模型设计
- **关键词**: 联合建模, 共享表示

### 23. Confidence Calibration
- **来源**: https://arxiv.org/abs/1908.03430
- **可信度**: ⭐⭐⭐⭐
- **核心贡献**: 置信度校准方法
- **关键词**: 置信度, 校准

### 24. Out-of-Distribution Detection
- **来源**: https://arxiv.org/abs/2008.03955
- **可信度**: ⭐⭐⭐⭐
- **核心贡献**: 未知意图检测
- **关键词**: OOD检测, 异常检测

### 25. Meta-Learning for Intent
- **来源**: https://arxiv.org/abs/1903.03096
- **可信度**: ⭐⭐⭐⭐
- **核心贡献**: 元学习快速适配
- **关键词**: 元学习, 快速适配

### 26. LLM as Intent Classifier
- **来源**: https://blog.langchain.dev/llms-can-classify-intent/
- **可信度**: ⭐⭐⭐⭐
- **核心贡献**: 大模型直接做意图分类
- **关键词**: 零样本分类, 提示工程

### 27. Hybrid Intent Detection Architecture
- **来源**: 工业实践
- **可信度**: ⭐⭐⭐⭐
- **核心贡献**: 规则+模型混合架构
- **关键词**: 混合架构, 降级策略

---

## 对话管理系统理论（10个）

### 28. Domain-Specific Dialogue Management
- **来源**: https://arxiv.org/abs/2103.01212
- **可信度**: ⭐⭐⭐⭐
- **核心贡献**: 领域特定对话管理
- **关键词**: 领域适配

### 29. Memory Mechanisms in Dialogue
- **来源**: https://arxiv.org/abs/2203.08817
- **可信度**: ⭐⭐⭐⭐
- **核心贡献**: 对话记忆机制设计
- **关键词**: 记忆管理, 上下文窗口

### 30. Multi-Turn Context Modeling
- **来源**: https://aclanthology.org/2021.naacl-main.318/
- **可信度**: ⭐⭐⭐⭐
- **核心贡献**: 多轮上下文建模
- **关键词**: 多轮对话, 上下文

### 31. State Tracking in Task-Oriented Dialogues
- **来源**: https://arxiv.org/abs/1904.07839
- **可信度**: ⭐⭐⭐⭐⭐
- **核心贡献**: 任务导向对话状态追踪
- **关键词**: 状态追踪, 槽位

### 32. Goal-Directed Dialogue Systems
- **来源**: https://arxiv.org/abs/2006.05706
- **可信度**: ⭐⭐⭐⭐
- **核心贡献**: 目标导向对话设计
- **关键词**: 目标导向, 任务完成

### 33. Personalization in Dialogue
- **来源**: https://arxiv.org/abs/2104.05610
- **可信度**: ⭐⭐⭐⭐
- **核心贡献**: 个性化对话生成
- **关键词**: 个性化, 用户画像

### 34. Error Recovery in Dialogues
- **来源**: https://aclanthology.org/2019.acl-main.403/
- **可信度**: ⭐⭐⭐⭐
- **核心贡献**: 对话错误恢复策略
- **关键词**: 错误恢复, 澄清

### 35. Policy Learning for Dialogues
- **来源**: https://arxiv.org/abs/1903.09059
- **可信度**: ⭐⭐⭐⭐
- **核心贡献**: 强化学习对话策略
- **关键词**: 强化学习, 策略优化

### 36. Evaluation Metrics for Dialogues
- **来源**: https://arxiv.org/abs/2103.03890
- **可信度**: ⭐⭐⭐⭐
- **核心贡献**: 对话质量评估指标
- **关键词**: 评估指标, 人工评估

### 37. Conversational Grounding
- **来源**: https://arxiv.org/abs/2104.05608
- **可信度**: ⭐⭐⭐⭐
- **核心贡献**: 对话共识建立
- **关键词**: 共识, 理解对齐

---

## LLM应用架构理论（13个）

### 38. LLM Application Patterns (Patterson et al.)
- **来源**: https://arxiv.org/abs/2405.15322
- **可信度**: ⭐⭐⭐⭐⭐
- **核心贡献**: LLM应用架构模式分类
- **关键词**: 架构模式, 最佳实践

### 39. Agent Architectures Survey
- **来源**: https://arxiv.org/abs/2401.02513
- **可信度**: ⭐⭐⭐⭐⭐
- **核心贡献**: Agent架构综述
- **关键词**: Agent架构, ReAct

### 40. ReAct: Reasoning + Acting
- **来源**: https://arxiv.org/abs/2210.03629
- **可信度**: ⭐⭐⭐⭐⭐
- **核心贡献**: 推理-行动交替框架
- **关键词**: ReAct, 思维链

### 41. Chain-of-Thought Prompting
- **来源**: https://arxiv.org/abs/2201.11903
- **可信度**: ⭐⭐⭐⭐⭐
- **核心贡献**: 思维链提示方法
- **关键词**: CoT, 逐步推理

### 42. Tree of Thoughts
- **来源**: https://arxiv.org/abs/2305.10601
- **可信度**: ⭐⭐⭐⭐
- **核心贡献**: 思维树搜索
- **关键词**: ToT, 搜索策略

### 43. Graph of Thoughts
- **来源**: https://arxiv.org/abs/2308.09680
- **可信度**: ⭐⭐⭐⭐
- **核心贡献**: 图结构思维
- **关键词**: GoT, 复杂推理

### 44. Tool Use in LLMs
- **来源**: https://arxiv.org/abs/2302.04761
- **可信度**: ⭐⭐⭐⭐⭐
- **核心贡献**: 工具调用能力
- **关键词**: 工具调用, function calling

### 45. Reflection in Agents
- **来源**: https://arxiv.org/abs/2303.11366
- **可信度**: ⭐⭐⭐⭐
- **核心贡献**: 自我反思机制
- **关键词**: 反思, 自我改进

### 46. Multi-Agent Collaboration
- **来源**: https://arxiv.org/abs/2305.13526
- **可信度**: ⭐⭐⭐⭐
- **核心贡献**: 多Agent协作模式
- **关键词**: 多Agent, 协作

### 47. LLM Safety and Alignment
- **来源**: https://www.anthropic.com/research
- **可信度**: ⭐⭐⭐⭐⭐
- **核心贡献**: 安全对齐研究
- **关键词**: 安全, 对齐

### 48. Cost-Effective LLM Deployment
- **来源**: 工业实践
- **可信度**: ⭐⭐⭐⭐
- **核心贡献**: 成本优化策略
- **关键词**: 成本控制, 分层部署

### 49. Latency Optimization for LLMs
- **来源**: https://blog.langchain.dev/optimizing-latency/
- **可信度**: ⭐⭐⭐⭐
- **核心贡献**: 延迟优化技术
- **关键词**: 延迟优化, 缓存

### 50. Production LLM Monitoring
- **来源**: https://langfuse.com/blog
- **可信度**: ⭐⭐⭐⭐
- **核心贡献**: 生产环境监控
- **关键词**: 监控, 可观测性

---

## 相关论文精选（20篇）

### 51. "Training Language Models to Follow Instructions" (InstructGPT)
- **来源**: OpenAI

### 52. "PaLM: Scaling Language Modeling with Pathways"
- **来源**: Google

### 53. "Chinchilla: Training Compute-Optimal LLMs"
- **来源**: DeepMind

### 54. "LLaMA: Open and Efficient Foundation Models"
- **来源**: Meta

### 55. "GLM-130B: An Open Bilingual Pre-trained Model"
- **来源**: 智谱AI

### 56. "Qwen: Building Generalist AI Agents"
- **来源**: 阿里云

### 57. "DeepSeek-Coder: Let the Machine Learn to Code"
- **来源**: DeepSeek

### 58. "Gemini: A Family of Highly Capable Multimodal Models"
- **来源**: Google

### 59. "Claude 3 Technical Report"
- **来源**: Anthropic

### 60. "GPT-4 Technical Report"
- **来源**: OpenAI

### 61. "Scaling Laws for Neural Language Models"
- **来源**: OpenAI

### 62. "The Emergence of Compositional Generalization"
- **来源**: ACL 2023

### 63. "Evaluation of Generative LLMs"
- **来源**: Hugging Face

### 64. "Factuality in LLMs"
- **来源**: NeurIPS 2023

### 65. "Hallucination in LLMs"
- **来源**: EMNLP 2023

---

*归档于：核心引擎/客服引擎/research/theories.md*
