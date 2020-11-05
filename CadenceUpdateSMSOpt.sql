USE [Campus6]
GO

/****** Object:  StoredProcedure [custom].[CadenceUpdateSMSOpt]    Script Date: 2020-11-05 14:58:34 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

-- =============================================
-- Author:		Wyatt Best
-- Create date: 2020-11-04
-- Description:	Updates a SMS Opt-In row.
-- =============================================
ALTER PROCEDURE [custom].[CadenceUpdateSMSOpt] @PCID NVARCHAR(10)
	,@Dept NVARCHAR(10)
	,@OptedIn BIT
	,@OPID NVARCHAR(8)
AS
BEGIN
	SET NOCOUNT ON;

	DECLARE @OptStatus NCHAR(1) = (
			SELECT CASE @OptedIn
					WHEN 1
						THEN 'A'
					WHEN 0
						THEN 'I'
					ELSE NULL
					END
			)

	UPDATE TELECOMMUNICATIONS
	SET [STATUS] = @OptStatus
		,COMMENTS = 'Updated ' + format(getdate(), 'g') + ' by ' + @OPID
		,REVISION_DATE = dbo.fnMakeDate(getdate())
		,REVISION_TIME = dbo.fnMakeTime(getdate())
		,REVISION_OPID = @OPID
	WHERE PEOPLE_ORG_CODE_ID = @PCID
		AND COM_TYPE = 'SMS' + @Dept

	SELECT @@ROWCOUNT
END
