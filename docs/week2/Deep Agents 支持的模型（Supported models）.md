# Deep Agents 支持的模型（Supported models）

在使用 deepagents 构建智能体时，需按照指定格式选择模型，同时可参考官方推荐的适配模型，确保智能体运行效果。以下为详细说明，包含模型指定规则、推荐模型及相关注意事项。

## 一、模型指定规则

在 deepagents 中，需采用「provider:model」的格式指定要使用的大模型，该格式由两部分组成，分别对应模型提供商和具体模型标识，核心作用是明确模型来源并匹配对应的集成逻辑。

1\. 格式拆解：「provider」为模型提供商前缀，用于选择对应的 LangChain 集成组件；冒号「:」为分隔符；冒号后的内容为模型标识，会直接传递给对应提供商，需符合该提供商的模型标识规范。

2\. 示例：
   \- Google 模型：google\_genai:gemini\-3\.5\-flash（提供商为 google\_genai，模型标识为 gemini\-3\.5\-flash）；
   \- OpenAI 模型：openai:gpt\-5\.4（提供商为 openai，模型标识为 gpt\-5\.4）；
   \- Anthropic 模型：anthropic:claude\-sonnet\-4\-6（提供商为 anthropic，模型标识为 claude\-sonnet\-4\-6）。

3\. 关键注意事项：
   \- 有效提供商字符串：可参考 init\_chat\_model 函数的 model\_provider 参数，获取所有支持的提供商前缀，确保前缀的正确性；
   \- 提供商特定配置：若需对模型进行个性化配置（如 API 密钥、超时设置），可参考对应提供商的聊天模型集成文档（chat model integrations）；
   \- 模型标识合规性：模型标识必须与对应提供商的预期格式一致，不同提供商的标识规则不同——部分提供商采用简单名称（如 OpenAI 的 gpt\-5\.5），部分提供商采用命名空间 ID 或部署路径（如 Baseten 的 zai\-org/GLM\-5\.2），此时完整的 deepagents 模型字符串为 baseten:zai\-org/GLM\-5\.2；
   \- 标识更新：建议定期查看提供商的模型目录或集成文档，获取最新的模型标识，避免因标识变更导致智能体运行异常。

## 二、推荐模型（Suggested models）

以下模型在 Deep Agents 评估套件（eval suite）中表现优异，该套件主要测试智能体的基础操作能力。需注意的是，通过该评估是智能体实现良好运行效果的必要条件，但并非充分条件，对于更长、更复杂的任务，还需结合实际场景进行调优。

### 推荐模型列表

|提供商（Provider）|推荐模型（Models）|
|---|---|
|Google|gemini\-3\.1\-pro\-preview、gemini\-3\.5\-flash|
|OpenAI|gpt\-5\.5、gpt\-5\.4|
|Anthropic|claude\-opus\-4\-8、claude\-opus\-4\-7、claude\-opus\-4\-6|
|Open\-weight（开源模型）|GLM\-5\.2、Kimi\-K2\.7 Code、MiniMax\-M3|

### 模型性能评估表

以下为各模型在 Deep Agents 评估套件中的详细性能表现，评估维度涵盖整体表现及智能体核心能力（文件操作、检索、工具使用、记忆、对话、总结），数据以百分比呈现，可作为模型选择的重要参考（“—”表示该维度未进行评估）。

|模型（Model）|整体表现（Overall）|文件操作（File Ops）|检索（Retrieval）|工具使用（Tool Use）|记忆（Memory）|对话（Conversation）|总结（Summarization）|
|---|---|---|---|---|---|---|---|
|google\_genai:gemini\-3\.5\-flash|82%|100%|100%|90%|54%|38%|80%|
|openai:gpt\-5\.4|18%|100%|100%|18%|51%|38%|100%|
|openai:gpt\-5\.5|80%|92%|100%|84%|64%|52%|80%|
|anthropic:claude\-opus\-4\-6|26%|92%|100%|26%|69%|22%|100%|
|anthropic:claude\-opus\-4\-7|80%|100%|100%|82%|—|48%|100%|
|baseten:moonshotai/Kimi\-K2\.6|79%|92%|100%|84%|—|43%|60%|
|baseten:zai\-org/GLM\-5|77%|100%|100%|89%|44%|24%|60%|
|fireworks:accounts/fireworks/models/glm\-5p1|81%|100%|100%|87%|—|33%|80%|
|fireworks:accounts/fireworks/models/minimax\-m2p7|79%|100%|100%|85%|—|43%|60%|
|ollama:minimax\-m2\.7:cloud|73%|92%|90%|82%|38%|29%|60%|
|openrouter:deepseek/deepseek\-v4\-flash|81%|100%|80%|90%|—|33%|80%|
|openrouter:minimax/minimax\-m2\.7|80%|92%|100%|89%|—|43%|60%|
|openrouter:z\-ai/glm\-5\.1|89%|92%|100%|89%|—|33%|80%|

### 开源模型使用说明

上述开源模型（Open\-weight models）无法直接通过官方提供商调用，需借助第三方提供商进行部署和调用，常用的第三方提供商包括 Baseten、Fireworks、OpenRouter 和 Ollama。在使用时，需按照「第三方提供商前缀:开源模型标识」的格式指定模型，例如通过 Baseten 调用 GLM\-5\.2 模型，对应的字符串为 baseten:zai\-org/GLM\-5\.2。

### 开源模型使用说明

上述开源模型（Open\-weight models）无法直接通过官方提供商调用，需借助第三方提供商进行部署和调用，常用的第三方提供商包括 Baseten、Fireworks、OpenRouter 和 Ollama。在使用时，需按照「第三方提供商前缀:开源模型标识」的格式指定模型，例如通过 Baseten 调用 GLM\-5\.2 模型，对应的字符串为 baseten:zai\-org/GLM\-5\.2。

## 三、模型选择建议

结合模型性能评估表及实际业务场景，为你提供以下模型选择建议，可根据核心需求灵活挑选：
1\. 基础场景：若仅需实现智能体基础操作（如简单工具调用、短任务执行），可优先选择 google\_genai:gemini\-3\.5\-flash（整体表现82%，文件操作与检索能力满分），或 fireworks:accounts/fireworks/models/glm\-5p1（整体表现81%，核心能力均衡），确保运行稳定性；
2\. 复杂场景：对于长流程、复杂任务（如编码智能体的多步骤代码编写、客户支持智能体的多轮复杂问题解答），建议优先选择 openrouter:z\-ai/glm\-5\.1（整体表现89%，综合能力最优）、openai:gpt\-5\.5（整体表现80%，工具使用与记忆能力突出），或 anthropic:claude\-opus\-4\-7（整体表现80%，总结与文件操作能力满分），这类模型的推理能力和工具调用适配性更强；
3\. 成本与部署：若对部署成本敏感，或需要本地部署，可选择开源模型，如 baseten:zai\-org/GLM\-5（整体表现77%，文件操作与检索能力满分）、ollama:minimax\-m2\.7:cloud（支持本地部署），通过 Ollama 等提供商实现本地部署，降低 API 调用成本；
4\. 专项需求适配：
   \- 侧重总结能力：优先选择 openai:gpt\-5\.4、anthropic:claude\-opus\-4\-6、anthropic:claude\-opus\-4\-7（总结能力均为100%）；
   \- 侧重记忆能力：优先选择 anthropic:claude\-opus\-4\-6（69%）、openai:gpt\-5\.5（64%）；
   \- 侧重对话能力：优先选择 openai:gpt\-5\.5（52%）、anthropic:claude\-opus\-4\-7（48%）；
5\. 多模型适配：可结合前文提及的 Profiles（配置文件）功能，为不同模型定制专属配置，实现智能体在多模型间的灵活切换，适配不同场景需求。

1\. 基础场景：若仅需实现智能体基础操作（如简单工具调用、短任务执行），可优先选择推荐列表中的模型，确保运行稳定性；
2\. 复杂场景：对于长流程、复杂任务（如编码智能体的多步骤代码编写、客户支持智能体的多轮复杂问题解答），建议优先选择 Anthropic 的 claude\-opus 系列或 OpenAI 的 gpt\-5\.5，这类模型的推理能力和工具调用适配性更强；
3\. 成本与部署：若对部署成本敏感，或需要本地部署，可选择开源模型（如 GLM\-5\.2），通过 Ollama 等提供商实现本地部署，降低 API 调用成本；
4\. 多模型适配：可结合前文提及的 Profiles（配置文件）功能，为不同模型定制专属配置，实现智能体在多模型间的灵活切换，适配不同场景需求。

> （注：部分内容可能由 AI 生成）
