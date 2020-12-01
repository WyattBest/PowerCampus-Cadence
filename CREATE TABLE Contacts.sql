USE [Campus6_suppMCNY]
GO

/****** Object:  Table [cadence].[Contacts]    Script Date: 2020-10-21 14:54:29 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

DROP TABLE [cadence].[Contacts]

CREATE TABLE [cadence].[Contacts] (
	[id] [uniqueidentifier] NOT NULL
	,[PEOPLE_CODE_ID] [nvarchar](10) NULL
	,[mobileNumber] [varchar](11) NOT NULL CHECK (cast([mobileNumber] AS BIGINT) BETWEEN 10000000000 AND 99999999999)
	,[CreateDatetime] [datetime] NOT NULL
	,[UpdateDatetime] [datetime] NOT NULL
	,[DepartmentCode] [nvarchar](10) NOT NULL
	,[optedOut] [bit] NOT NULL
	,PRIMARY KEY CLUSTERED ([id] ASC) WITH (
		PAD_INDEX = OFF
		,STATISTICS_NORECOMPUTE = OFF
		,IGNORE_DUP_KEY = OFF
		,ALLOW_ROW_LOCKS = ON
		,ALLOW_PAGE_LOCKS = ON
		)
	ON [PRIMARY]
	) ON [PRIMARY]
GO

ALTER TABLE [cadence].[Contacts] ADD DEFAULT(newid())
FOR [id]
GO

ALTER TABLE [cadence].[Contacts] ADD DEFAULT(getdate())
FOR [CreateDatetime]
GO

ALTER TABLE [cadence].[Contacts] ADD DEFAULT(getdate())
FOR [UpdateDatetime]
GO


