import React from 'react';
import ReactMarkdown from 'react-markdown';

interface MarkdownContentProps {
  content: string;
}

export const MarkdownContent: React.FC<MarkdownContentProps> = ({ content }) => (
  <div className="md-content">
    <ReactMarkdown
      components={{
        table: (props) => (
          <div className="md-table-wrap">
            <table {...props} />
          </div>
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  </div>
);
