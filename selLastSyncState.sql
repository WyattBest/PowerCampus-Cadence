USE [Campus6_suppMCNY]
GO

/****** Object:  StoredProcedure [cadence].[selLastSyncState]    Script Date: 2020-12-15 16:57:00 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO


-- =============================================
-- Author:		Wyatt Best
-- Create date: 2020-10-23
-- Description:	Returns rows from cadence.Contacts according to department code.
-- =============================================
CREATE PROCEDURE [cadence].[selLastSyncState] @dept NVARCHAR(10)
AS
BEGIN
	SET NOCOUNT ON;

	--If we ever need to send dates to Cadence's API, use 'ISO 8601 format in UTC' like 2019-07-08T18:05:48Z
	--DECLARE @TimeZone VARCHAR(50)
	--EXEC master.dbo.xp_regread 'HKEY_LOCAL_MACHINE'
	--	,'SYSTEM\CurrentControlSet\Control\TimeZoneInformation'
	--	,'TimeZoneKeyName'
	--	,@TimeZone OUT
	SELECT TOP 10 [id] --Debug
		,[PEOPLE_CODE_ID] [uniqueCampusId]
		,[mobileNumber]
		,[CreateDatetime]
		--,format(CONVERT(DATETIME, [CreateDatetime] AT TIME ZONE @TimeZone AT TIME ZONE 'UTC'), 'yyyy-MM-ddTHH:mm:ssZ') [CreateDatetime]
		--,format(CONVERT(DATETIME, [UpdateDatetime] AT TIME ZONE @TimeZone AT TIME ZONE 'UTC'), 'yyyy-MM-ddTHH:mm:ssZ') [UpdateDatetime]
		,[DepartmentCode]
		,[optedOut]
	FROM [Contacts]
	WHERE DepartmentCode = @dept
		AND PEOPLE_CODE_ID IS NOT NULL
	ORDER BY PEOPLE_CODE_ID --Debug
END
GO

