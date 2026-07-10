import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { ReactNode } from 'react';
import { UiLanguageProvider, useUiLanguage } from '../../../contexts/UiLanguageContext';
import { getFieldDescriptionZh, getFieldTitleZh } from '../../../utils/systemConfigI18n';
import { UI_LANGUAGE_STORAGE_KEY } from '../../../utils/uiLanguage';
import { SettingsField } from '../SettingsField';

describe('SettingsField', () => {
  it('prefers localized Chinese field titles over backend schema titles', () => {
    render(
      <SettingsField
        item={{
          key: 'STOCK_LIST',
          value: '600519',
          rawValueExists: true,
          isMasked: false,
          schema: {
            key: 'STOCK_LIST',
            title: 'Stock List',
            category: 'base',
            dataType: 'string',
            uiControl: 'text',
            isSensitive: false,
            isRequired: false,
            isEditable: true,
            options: [],
            validation: {},
            displayOrder: 1,
          },
        }}
        value="600519"
        onChange={vi.fn()}
      />
    );

    expect(screen.getByLabelText('Stock List')).toBeInTheDocument();
    expect(screen.queryByLabelText('Stock List')).not.toBeInTheDocument();
  });

  it('localizes TickFlow field descriptions instead of falling back to backend English schema', () => {
    render(
      <SettingsField
        item={{
          key: 'TICKFLOW_PRIORITY',
          value: '2',
          rawValueExists: false,
          isMasked: false,
          schema: {
            key: 'TICKFLOW_PRIORITY',
            title: 'TickFlow Priority',
            description: 'Priority for TickFlow daily K-line fetcher. Lower numbers are tried earlier.',
            category: 'data_source',
            dataType: 'integer',
            uiControl: 'number',
            isSensitive: false,
            isRequired: false,
            isEditable: true,
            options: [],
            validation: { min: 0, max: 99 },
            displayOrder: 16,
            helpKey: 'settings.data_source.TICKFLOW_PRIORITY',
          },
        }}
        value="2"
        onChange={vi.fn()}
      />
    );

    expect(screen.getByLabelText('TickFlow daily K-line priority')).toBeInTheDocument();
    expect(screen.getByText(/控制 TickFlow 在 A 股日 K 数据源回退链中的尝试顺序/)).toBeInTheDocument();
    expect(screen.queryByText(/Priority for TickFlow daily K-line fetcher/)).not.toBeInTheDocument();
  });
  it('uses schema key for TickFlow localization when the runtime item key differs', () => {
    render(
      <SettingsField
        item={{
          key: 'runtime.tickflow.priority',
          value: '2',
          rawValueExists: false,
          isMasked: false,
          schema: {
            key: 'TICKFLOW_PRIORITY',
            title: 'TickFlow Priority',
            description: 'Priority for TickFlow daily K-line fetcher. Lower numbers are tried earlier.',
            category: 'data_source',
            dataType: 'integer',
            uiControl: 'number',
            isSensitive: false,
            isRequired: false,
            isEditable: true,
            options: [],
            validation: { min: 0, max: 99 },
            displayOrder: 16,
            helpKey: 'settings.data_source.TICKFLOW_PRIORITY',
          },
        }}
        value="2"
        onChange={vi.fn()}
      />
    );

    expect(screen.getByLabelText(getFieldTitleZh('TICKFLOW_PRIORITY', ''))).toBeInTheDocument();
    expect(screen.getByText(getFieldDescriptionZh('TICKFLOW_PRIORITY', ''))).toBeInTheDocument();
    expect(screen.queryByLabelText('TickFlow Priority')).not.toBeInTheDocument();
    expect(screen.queryByText(/Priority for TickFlow daily K-line fetcher/)).not.toBeInTheDocument();
  });
  it('renders sensitive field metadata and validation errors', () => {
    const onChange = vi.fn();

    render(
      <SettingsField
        item={{
          key: 'OPENAI_API_KEY',
          value: 'secret',
          rawValueExists: true,
          isMasked: false,
          schema: {
            key: 'OPENAI_API_KEY',
            category: 'ai_model',
            dataType: 'string',
            uiControl: 'password',
            isSensitive: true,
            isRequired: true,
            isEditable: true,
            options: [],
            validation: {},
            displayOrder: 1,
          },
        }}
        value="secret"
        onChange={onChange}
        issues={[
          {
            key: 'OPENAI_API_KEY',
            code: 'required',
            message: 'API Key is required',
            severity: 'error',
          },
        ]}
      />
    );

    expect(screen.getByText('Sensitive')).toBeInTheDocument();
    expect(screen.getByText('API Key is required')).toBeInTheDocument();

    const input = screen.getByLabelText('OpenAI API Key');
    fireEvent.focus(input);
    fireEvent.change(input, {
      target: { value: 'updated-secret' },
    });

    expect(onChange).toHaveBeenCalledWith('OPENAI_API_KEY', 'updated-secret');
  });

  it('renders multi-value sensitive fields with external delete actions', () => {
    const onChange = vi.fn();

    render(
      <SettingsField
        item={{
          key: 'OPENAI_API_KEYS',
          value: 'secret-a,secret-b',
          rawValueExists: true,
          isMasked: false,
          schema: {
            key: 'OPENAI_API_KEYS',
            category: 'ai_model',
            dataType: 'string',
            uiControl: 'password',
            isSensitive: true,
            isRequired: false,
            isEditable: true,
            options: [],
            validation: { multiValue: true },
            displayOrder: 1,
          },
        }}
        value="secret-a,secret-b"
        onChange={onChange}
      />
    );

    expect(screen.getAllByRole('button', { name: 'Show' })).toHaveLength(2);
    expect(screen.getAllByRole('button', { name: 'Delete' })).toHaveLength(2);
  });

  it('allows optional select fields to be cleared when schema provides an empty option', () => {
    const onChange = vi.fn();

    render(
      <SettingsField
        item={{
          key: 'NOTIFICATION_MIN_SEVERITY',
          value: 'warning',
          rawValueExists: true,
          isMasked: false,
          schema: {
            key: 'NOTIFICATION_MIN_SEVERITY',
            title: 'Notification Minimum Severity',
            category: 'notification',
            dataType: 'string',
            uiControl: 'select',
            isSensitive: false,
            isRequired: false,
            isEditable: true,
            options: [
              { label: 'Not set', value: '' },
              { label: 'info', value: 'info' },
              { label: 'warning', value: 'warning' },
              { label: 'error', value: 'error' },
              { label: 'critical', value: 'critical' },
            ],
            validation: { enum: ['', 'info', 'warning', 'error', 'critical'] },
            displayOrder: 69,
          },
        }}
        value="warning"
        onChange={onChange}
      />
    );

    const select = screen.getByLabelText('Minimum notification severity');
    expect(screen.getByRole('option', { name: 'Not set' })).not.toBeDisabled();
    expect(screen.queryByRole('option', { name: 'Please select' })).not.toBeInTheDocument();

    fireEvent.change(select, { target: { value: '' } });

    expect(onChange).toHaveBeenCalledWith('NOTIFICATION_MIN_SEVERITY', '');
  });

  it('shows the schema default for select fields when no explicit env value exists', () => {
    const onChange = vi.fn();

    render(
      <SettingsField
        item={{
          key: 'GENERATION_BACKEND',
          value: '',
          rawValueExists: false,
          isMasked: false,
          schema: {
            key: 'GENERATION_BACKEND',
            title: 'Generation Backend',
            category: 'ai_model',
            dataType: 'string',
            uiControl: 'select',
            isSensitive: false,
            isRequired: false,
            isEditable: true,
            defaultValue: 'litellm',
            options: [{ label: 'Default model settings', value: 'litellm' }],
            validation: { enum: ['litellm'] },
            displayOrder: 1,
          },
        }}
        value=""
        onChange={onChange}
      />
    );

    expect(screen.getByLabelText('Analysis generation method')).toHaveValue('litellm');
    expect(onChange).not.toHaveBeenCalled();
  });

  it('renders localized labels for real system config select options', () => {
    const selectCases = [
      {
        key: 'NEWS_STRATEGY_PROFILE',
        category: 'data_source',
        options: ['ultra_short', 'short', 'medium', 'long'],
        expectedLabels: ['Ultra short (1 day)', 'Short (3 days)', 'Medium (7 days)', 'Long (30 days)'],
      },
      {
        key: 'REPORT_TYPE',
        category: 'notification',
        options: ['simple', 'full', 'brief'],
        expectedLabels: ['Simple', 'Full', 'Brief'],
      },
      {
        key: 'LOG_LEVEL',
        category: 'system',
        options: ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        expectedLabels: ['Debug', 'Info', 'Warning', 'Error', 'Critical'],
      },
    ] as const;

    selectCases.forEach(({ key, category, options, expectedLabels }) => {
      const { unmount } = render(
        <SettingsField
          item={{
            key,
            value: options[0],
            rawValueExists: true,
            isMasked: false,
            schema: {
              key,
              title: key,
              category,
              dataType: 'string',
              uiControl: 'select',
              isSensitive: false,
              isRequired: false,
              isEditable: true,
              options: [...options],
              validation: {},
              displayOrder: 1,
            },
          }}
          value={options[0]}
          onChange={() => undefined}
        />
      );

      expectedLabels.forEach((label) => {
        expect(screen.getByRole('option', { name: label })).toBeInTheDocument();
      });

      options.forEach((rawOption) => {
        expect(screen.queryByRole('option', { name: rawOption })).not.toBeInTheDocument();
      });

      unmount();
    });
  });

  it('renders MARKET_REVIEW_REGION as free-text field with comma-separated defaults', () => {
    const onChange = vi.fn();

    render(
      <SettingsField
        item={{
          key: 'MARKET_REVIEW_REGION',
          value: 'cn,jp',
          rawValueExists: true,
          isMasked: false,
          schema: {
            key: 'MARKET_REVIEW_REGION',
            category: 'system',
            dataType: 'string',
            uiControl: 'text',
            isSensitive: false,
            isRequired: false,
            isEditable: true,
            options: [],
            validation: {},
            displayOrder: 1,
          },
        }}
        value="cn,jp"
        onChange={onChange}
      />
    );

    const input = screen.getByLabelText('Market review market') as HTMLInputElement;
    expect(input).toHaveValue('cn,jp');
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument();

    fireEvent.change(input, {
      target: { value: 'cn,jp,kr' },
    });

    expect(onChange).toHaveBeenCalledWith('MARKET_REVIEW_REGION', 'cn,jp,kr');
  });

  it('renders context compression profile options with Chinese labels', () => {
    const onChange = vi.fn();

    render(
      <SettingsField
        item={{
          key: 'AGENT_CONTEXT_COMPRESSION_PROFILE',
          value: 'balanced',
          rawValueExists: true,
          isMasked: false,
          schema: {
            key: 'AGENT_CONTEXT_COMPRESSION_PROFILE',
            category: 'agent',
            dataType: 'string',
            uiControl: 'select',
            isSensitive: false,
            isRequired: false,
            isEditable: true,
            options: [
              { label: 'Cost first', value: 'cost' },
              { label: 'Balanced (recommended)', value: 'balanced' },
              { label: 'Long context raw first', value: 'long_context_raw_first' },
            ],
            validation: {
              enum: ['cost', 'balanced', 'long_context_raw_first'],
            },
            displayOrder: 72,
          },
        }}
        value="balanced"
        onChange={onChange}
      />
    );

    expect(screen.getByLabelText('Context compression strategy')).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Cost first' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Balanced (recommended)' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Long context raw first' })).toBeInTheDocument();
  });

  it('renders blank-value preset guidance for context compression numeric fields', () => {
    const onChange = vi.fn();

    render(
      <>
        <SettingsField
          item={{
            key: 'AGENT_CONTEXT_COMPRESSION_TRIGGER_TOKENS',
            value: '',
            rawValueExists: false,
            isMasked: false,
            schema: {
              key: 'AGENT_CONTEXT_COMPRESSION_TRIGGER_TOKENS',
              category: 'agent',
              dataType: 'integer',
              uiControl: 'number',
              isSensitive: false,
              isRequired: false,
              isEditable: true,
              options: [],
              validation: { min: 1000 },
              displayOrder: 73,
            },
          }}
          value=""
          onChange={onChange}
        />
        <SettingsField
          item={{
            key: 'AGENT_CONTEXT_PROTECTED_TURNS',
            value: '',
            rawValueExists: false,
            isMasked: false,
            schema: {
              key: 'AGENT_CONTEXT_PROTECTED_TURNS',
              category: 'agent',
              dataType: 'integer',
              uiControl: 'number',
              isSensitive: false,
              isRequired: false,
              isEditable: true,
              options: [],
              validation: { min: 1 },
              displayOrder: 74,
            },
          }}
          value=""
          onChange={onChange}
        />
      </>
    );

    expect(screen.getByLabelText('Compression trigger threshold (tokens)')).toBeInTheDocument();
    expect(screen.getByLabelText('Protected turns')).toBeInTheDocument();
    expect(screen.getByText(/估算历史 token 超过该值时触发摘要/)).toHaveTextContent('Leave blank to follow the current context compression strategy profile default');
    expect(screen.getByText(/压缩时最近 N 个用户轮次及其后的回复保持原文/)).toHaveTextContent('Leave blank to follow the current context compression strategy profile default');
  });

  it('renders localized custom webhook body template guidance', () => {
    const onChange = vi.fn();

    render(
      <SettingsField
        item={{
          key: 'CUSTOM_WEBHOOK_BODY_TEMPLATE',
          value: '',
          rawValueExists: false,
          isMasked: false,
          schema: {
            key: 'CUSTOM_WEBHOOK_BODY_TEMPLATE',
            category: 'notification',
            dataType: 'string',
            uiControl: 'textarea',
            isSensitive: false,
            isRequired: false,
            isEditable: true,
            options: [],
            validation: {},
            displayOrder: 52,
          },
        }}
        value=""
        onChange={onChange}
      />
    );

    expect(screen.getByLabelText('Custom Webhook Body template')).toBeInTheDocument();
    expect(screen.getByText(/会先于 Bark、Slack、Discord 等自动 payload 生效/)).toBeInTheDocument();
    expect(screen.getByText(/裸 \$content \/ \$title 不做 JSON 转义/)).toBeInTheDocument();
  });

  it('opens detailed field help when help metadata is available', () => {
    render(
      <SettingsField
        item={{
          key: 'STOCK_LIST',
          value: '600519,300750',
          rawValueExists: true,
          isMasked: false,
          schema: {
            key: 'STOCK_LIST',
            category: 'base',
            dataType: 'array',
            uiControl: 'textarea',
            isSensitive: false,
            isRequired: false,
            isEditable: true,
            options: [],
            validation: {},
            displayOrder: 1,
            helpKey: 'settings.base.STOCK_LIST',
            examples: ['STOCK_LIST=600519,300750,002594'],
            docs: [
              {
                label: 'Full Guide',
                href: 'https://example.com/full-guide',
              },
            ],
            warningCodes: [],
          },
        }}
        value="600519,300750"
        onChange={() => undefined}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: 'View Stock list configuration help' }));

    expect(screen.getByRole('dialog', { name: 'Stock List' })).toBeInTheDocument();
    expect(screen.getByText('STOCK_LIST=600519,300750,002594')).toBeInTheDocument();
    const docLink = screen.getByRole('link', { name: /完整指南/ });
    expect(docLink).toHaveAttribute('href', 'https://example.com/full-guide');

    const closeButtons = screen.getAllByRole('button', { name: 'Close configuration help' });
    expect(closeButtons[0].tabIndex).toBe(-1);
    const closeButton = closeButtons.find((button) => button.tabIndex !== -1);
    expect(closeButton).toBeDefined();

    closeButton?.focus();
    fireEvent.keyDown(document, { key: 'Tab', shiftKey: true });
    expect(docLink).toHaveFocus();

    fireEvent.keyDown(document, { key: 'Tab' });
    expect(closeButton).toHaveFocus();

    fireEvent.keyDown(document, { key: 'Escape' });
    expect(screen.queryByRole('dialog', { name: 'Stock List' })).not.toBeInTheDocument();
  });

  it('keeps generation channel help user-facing without env key or examples', () => {
    render(
      <SettingsField
        item={{
          key: 'GENERATION_BACKEND',
          value: 'litellm',
          rawValueExists: true,
          isMasked: false,
          schema: {
            key: 'GENERATION_BACKEND',
            title: 'Generation Backend',
            category: 'ai_model',
            dataType: 'string',
            uiControl: 'select',
            isSensitive: false,
            isRequired: false,
            isEditable: true,
            options: [{ label: 'Default model settings', value: 'litellm' }],
            validation: { enum: ['litellm'] },
            displayOrder: 1,
            helpKey: 'settings.ai_model.GENERATION_BACKEND',
            examples: ['GENERATION_BACKEND=litellm'],
            warningCodes: [],
          },
        }}
        value="litellm"
        onChange={() => undefined}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: 'View Analysis generation method configuration help' }));

    const dialog = screen.getByRole('dialog', { name: 'Analysis generation method' });
    expect(dialog).toHaveTextContent('Determines how the system generates');
    expect(dialog).not.toHaveTextContent('GENERATION_BACKEND');
    expect(dialog).not.toHaveTextContent('Config example');
    expect(dialog).not.toHaveTextContent('Phase 1');
    expect(dialog).toHaveTextContent('Corresponding CLI is installed and logged in on this machine');
    expect(dialog).toHaveTextContent('Default model settings continue to use existing API Key');
    expect(dialog).not.toHaveTextContent('Advanced notes');
    expect(dialog).not.toHaveTextContent('LiteLLM');
  });

  it('describes agent auto generation without exposing implementation labels as the primary UI copy', () => {
    render(
      <SettingsField
        item={{
          key: 'AGENT_GENERATION_BACKEND',
          value: 'auto',
          rawValueExists: true,
          isMasked: false,
          schema: {
            key: 'AGENT_GENERATION_BACKEND',
            title: 'Agent Generation Backend',
            category: 'agent',
            dataType: 'string',
            uiControl: 'select',
            isSensitive: false,
            isRequired: false,
            isEditable: true,
            options: [
              { label: 'Auto', value: 'auto' },
              { label: 'Default model settings', value: 'litellm' },
            ],
            validation: { enum: ['auto', 'litellm'] },
            displayOrder: 1,
            helpKey: 'settings.agent.AGENT_GENERATION_BACKEND',
            examples: [],
            warningCodes: [],
          },
        }}
        value="auto"
        onChange={() => undefined}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: 'View Ask-Stock generation method configuration help' }));

    const dialog = screen.getByRole('dialog', { name: 'Ask-Stock generation method' });
    expect(dialog).toHaveTextContent('The system will choose the currently available method');
    expect(dialog).toHaveTextContent('如果不确定，选择“自动”即可');
    expect(dialog).toHaveTextContent('This setting only affects Ask-Stock assistant');
    expect(dialog).not.toHaveTextContent('Advanced notes');
    expect(dialog).not.toHaveTextContent('LiteLLM');
    expect(dialog).not.toHaveTextContent('Prioritizes currently available');
  });

  it('uses per-field schema titles even when helpKey is shared by multiple fields', () => {
    const restoreLanguage = localStorage.getItem(UI_LANGUAGE_STORAGE_KEY);
    localStorage.setItem(UI_LANGUAGE_STORAGE_KEY, 'en');

    try {
      const SchemaTitleSwitcher = ({ children }: { children: ReactNode }) => {
        const { setLanguage } = useUiLanguage();
        return (
          <div>
            <button type="button" onClick={() => setLanguage('en')}>
              switch-en
            </button>
            {children}
          </div>
        );
      };

      render(
        <UiLanguageProvider>
          <SchemaTitleSwitcher>
            <SettingsField
              item={{
                key: 'OPENAI_MODEL',
                value: 'gemini/gemini-3.1-pro-preview',
                rawValueExists: true,
                isMasked: false,
                schema: {
                  key: 'OPENAI_MODEL',
                  category: 'ai_model',
                  dataType: 'string',
                  uiControl: 'text',
                  isSensitive: false,
                  isRequired: false,
                  isEditable: true,
                  options: [],
                  validation: {},
                  displayOrder: 10,
                  title: 'Primary model',
                  helpKey: 'settings.llm_channel.primary_model',
                  description: 'Primary model description',
                },
              }}
              value="gemini/gemini-3.1-pro-preview"
              onChange={vi.fn()}
            />
            <SettingsField
              item={{
                key: 'OPENAI_VISION_MODEL',
                value: 'gemini/gemini-2.0-flash',
                rawValueExists: true,
                isMasked: false,
                schema: {
                  key: 'OPENAI_VISION_MODEL',
                  category: 'ai_model',
                  dataType: 'string',
                  uiControl: 'text',
                  isSensitive: false,
                  isRequired: false,
                  isEditable: true,
                  options: [],
                  validation: {},
                  displayOrder: 11,
                  title: 'Vision model',
                  helpKey: 'settings.llm_channel.primary_model',
                  description: 'Vision model description',
                },
              }}
              value="gemini/gemini-2.0-flash"
              onChange={vi.fn()}
            />
          </SchemaTitleSwitcher>
        </UiLanguageProvider>
      );

      fireEvent.click(screen.getByRole('button', { name: 'switch-en' }));

      expect(screen.getByLabelText('Primary model')).toBeInTheDocument();
      expect(screen.getByLabelText('Vision model')).toBeInTheDocument();
    } finally {
      if (restoreLanguage) {
        localStorage.setItem(UI_LANGUAGE_STORAGE_KEY, restoreLanguage);
      } else {
        localStorage.removeItem(UI_LANGUAGE_STORAGE_KEY);
      }
    }
  });
});
