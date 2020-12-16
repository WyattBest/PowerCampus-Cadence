USE [Campus6]
GO

/****** Object:  StoredProcedure [custom].[CadenceSelContact]    Script Date: 2020-12-15 16:58:20 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO


-- =============================================
-- Author:		Wyatt Best
-- Create date: 2020-11-30
-- Description:	Selects core demographic fields for a single contact.
-- =============================================
CREATE PROCEDURE [custom].[CadenceSelContact] @PCID NVARCHAR(10)
AS
BEGIN
	SET NOCOUNT ON;

	SELECT PEOPLE_CODE_ID [uniqueCampusId]
		,dbo.fnPeopleOrgName(PEOPLE_CODE_ID, 'FN') [firstName]
		,dbo.fnPeopleOrgName(PEOPLE_CODE_ID, 'LN') [lastName]
		,Phone.*
	FROM PEOPLE P
	OUTER APPLY (
		SELECT TOP 1 CASE 
				WHEN CountryId = 240 --US country code
					THEN '1' + PP.PhoneNumber
				ELSE '??'
				END AS [mobileNumber]
		FROM PersonPhone PP
		WHERE PP.PersonId = P.PersonId
			AND DoNotCallReason IS NULL
			AND PhoneType = 'MOBILE1'
		ORDER BY CASE 
				WHEN P.PrimaryPhoneId = PP.PersonPhoneId
					THEN GETDATE()
				ELSE PP.Revision_Date + PP.Revision_Time
				END DESC
		) AS Phone
	WHERE PEOPLE_CODE_ID = @PCID
	ORDER BY PEOPLE_CODE_ID --Debug
END
GO

